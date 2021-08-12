from typing import List
import cupy
from .base import Model
from ..layers.transformer_block import TransformerBlockDecoder, TransformerBlockEncoder
from ..layers.encoder_kv import EncoderKeyValueProjection
from ..layers.position_bias import PositionBias
from ..layers.embedding import Embedding
from ..layers.layer_norm import LayerNorm
from ..layers.mask import InputMask
from ..layers.lm_head import LMHead
from ..layers.layer_list import LayerList
from ..configuration import CPM2Configuration
from ..allocator import ReusedAllocator, SizeLimitedAllocator
import numpy as np
import logging

logger = logging.getLogger(__name__)

class CPM2(Model):
    def __init__(self, config : CPM2Configuration):
        # Build Model
        logger.info("Building model")

        self.memory_overlap = config.MEMORY_OVERLAP
        if self.memory_overlap:
            self.overlap_layers = config.OVERLAP_LAYERS
        else:
            self.overlap_layers = max(config.NUM_ENCODER_LAYERS, config.NUM_DECODER_LAYERS)
        self.encoder_only = config.ENCODER_ONLY

        self.input_embedding = Embedding(config.VOCAB_SIZE, config.DIM_MODEL, ltype=Embedding.TYPE_F16)
        self.input_mask = InputMask(is_decoder=False)

        self.encoder_position_bias = PositionBias(config.NUM_POSITION_BUCKETS, config.NUM_HEADS, False, PositionBias.TYPE_F32)
        self.num_encoder = config.NUM_ENCODER_LAYERS
        self.encoder = LayerList([
            TransformerBlockEncoder(config.DIM_MODEL, config.DIM_FF, config.DIM_KV, config.NUM_HEADS)
                for _ in range(config.NUM_ENCODER_LAYERS)
        ])
        self.encoder_final_layer_nrom = LayerNorm(config.DIM_MODEL)
        self.num_heads = config.NUM_HEADS

        if not self.encoder_only:
            self.decoder_position_bias = PositionBias(config.NUM_POSITION_BUCKETS, config.NUM_HEADS, True, PositionBias.TYPE_F32)
            self.encoder_kv = EncoderKeyValueProjection(config.NUM_DECODER_LAYERS, config.DIM_MODEL, config.DIM_KV, config.NUM_HEADS)
            self.lm_head = LMHead(config.VOCAB_SIZE, config.DIM_MODEL, ltype=LMHead.TYPE_F32)
            self.num_decoder = config.NUM_DECODER_LAYERS
            self.decoder = LayerList([
                TransformerBlockDecoder(config.DIM_MODEL, config.DIM_FF, config.DIM_KV, config.NUM_HEADS)
                    for _ in range(config.NUM_DECODER_LAYERS)
            ])
            self.decoder_final_layer_nrom = LayerNorm(config.DIM_MODEL)

        if config.MODEL_PATH is not None:
            # init parameter
            self.device = cupy.cuda.Device(config.DEVICE)
            with self.device:
                logger.info("Start loading parameters from disk to cpu")
                self.load( open(config.MODEL_PATH, "rb") )

                logger.info("Start loading parameters from cpu to gpu")
                
                load_stream = cupy.cuda.Stream()
                
                if self.memory_overlap:
                    mx_size = 0
                    for i in range(config.NUM_ENCODER_LAYERS):
                        mx_size = max(self.encoder[i].nbytes, mx_size)
                    for i in range(config.NUM_DECODER_LAYERS):
                        mx_size = max(self.decoder[i].nbytes, mx_size)

                    temp_size = self._get_preapre_buffer_size()
                    overlap_size = mx_size * self.overlap_layers * 4
                    other_size = self.nbytes - self.encoder.nbytes - self.decoder.nbytes

                    logger.info("Using overlap loader: overlap_size %d, temp_size %d, other_size: %d, dynamic_memory %d, memory_limit %d", overlap_size, temp_size, other_size, config.DYNAMIC_MEMORY, config.MEMORY_LIMIT)
                    if overlap_size + other_size + temp_size * 2 + config.DYNAMIC_MEMORY > config.MEMORY_LIMIT:
                        raise ValueError("memory limit not enough, at least %d bytes, bug got %d bytes" % (overlap_size + other_size + temp_size * 2 + config.DYNAMIC_MEMORY, config.MEMORY_LIMIT))
                    self.parameter_allocator = ReusedAllocator(other_size + (overlap_size // 2), temp_size)
                    self.overlap_allocator = [ReusedAllocator(overlap_size // 4, temp_size), ReusedAllocator(overlap_size // 4, temp_size)]

                    self.variable_allocator = SizeLimitedAllocator(config.MEMORY_LIMIT - other_size - overlap_size - temp_size * 2, 0)

                    self.variable_allocator.alloc(config.DYNAMIC_MEMORY) # preallocate

                    for name, layer in self._sub_layers.items():
                        if name in ["encoder", "decoder"]:
                            # move first overlap_size layers to device
                            for i in range(min(self.overlap_layers, len(layer))):
                                layer[i].to_device( self.parameter_allocator, load_stream )
                        else:
                            layer.to_device( self.parameter_allocator, load_stream  )
                else:
                    if self.nbytes + config.DYNAMIC_MEMORY < config.MEMORY_LIMIT:
                        raise ValueError("memory limit not enough, at least %d bytes, bug got %d bytes" % (self.nbytes + config.DYNAMIC_MEMORY, config.MEMORY_LIMIT))
                    
                    temp_size = self._get_preapre_buffer_size()
                    logger.info("Using static loader: total: %d, temp_size %d, dynamic_memory %d, memory_limit %d", self.nbytes, temp_size, config.DYNAMIC_MEMORY, config.MEMORY_LIMIT)
                    self.parameter_allocator = ReusedAllocator(self.nbytes, temp_size)
                    self.variable_allocator = SizeLimitedAllocator(config.MEMORY_LIMIT - self.nbytes, 0)

                    self.variable_allocator.alloc(config.DYNAMIC_MEMORY) # preallocate

                    self.to_device(self.parameter_allocator, load_stream)
                
                self.load_stream = cupy.cuda.Stream()
                self.device.synchronize()

            logger.info("Cleaning useless parameters on cpu")
            if self.memory_overlap:
                for name, layer in self._sub_layers.items():
                    if name in ["encoder", "decoder"]:
                        # move first overlap_size layers to device
                        for i in range(self.overlap_layers):
                            layer[i]._remove_data()
                    else:
                        layer._remove_data()
            else:
                self._remove_data()
            logger.info("End of model initialization")


    def forward(self, input_idx : np.ndarray, input_length : List[int]):

        tmp = []
        with self.device:
            load_stream = self.load_stream
            calc_stream = cupy.cuda.get_current_stream()
            load_event = load_stream.record()
            calc_event = calc_stream.record()

            batch_size, seq_len = input_idx.shape

            x = self.input_embedding.forward(self.variable_allocator, input_idx)
            encoder_attn_mask = self.input_mask.forward(self.variable_allocator, input_length, seq_len)
            x.value = x.value.transpose((0, 2, 1))
            x_pos = self.encoder_position_bias.forward(self.variable_allocator, seq_len, seq_len)
            assert len(x_pos.value.shape) == 4
            assert x_pos.value.shape == (1, self.num_heads, seq_len, seq_len)

            for i in range(self.num_encoder):
                if i % self.overlap_layers == 0:
                    calc_stream.wait_event(load_event)
                logger.info("Calc encoder layer %d", i)
                x = self.encoder[i].forward(
                    self.variable_allocator, 
                    x,
                    encoder_attn_mask,
                    x_pos if i == 0 else None,
                    True
                )
                if i % self.overlap_layers == self.overlap_layers - 1 and i + 1 < self.num_encoder:
                    overlap_idx = ((i + 1) // self.overlap_layers) % 2
                    olp_allocator = self.overlap_allocator[overlap_idx]
                    olp_allocator.reset()
                    load_stream.wait_event(calc_event)
                    for j in range(i + 1, min(i + self.overlap_layers, self.num_encoder) + 1):
                        logger.info("Load encoder layer %d", j)
                        self.encoder[j].to_device(olp_allocator, load_stream)
                    
                    calc_event = calc_stream.record()
                    load_event = load_stream.record()
                self.device.synchronize()
                tmp.append(cupy.asnumpy(x.value[0].T))
        with open("hidden_i8.npy", "wb") as f:
            np.save(f, np.stack(tmp).astype(np.float16))
        return x