import tkinter as tk
import keyboard
import threading
import time

# 全局变量，用于记录键盘输入的时间戳和按键次数
last_key_timestamp = 0
key_count = 0

# 定义门限值，每秒敲击键盘次数不超过30个键位
threshold = 1 / 30

# 创建GUI窗口
window = tk.Tk()
window.title("HID攻击防护")
window.geometry("300x100")

# 创建提示标签
label = tk.Label(window, text="正常输入设备", font=("宋体", 16))
label.pack()

# 标志位，用于表示是否检测到异常输入
abnormal_detected = False

# 标志位，用于表示是否禁止输入
input_blocked = False

def check_key_interval(event):
    global last_key_timestamp, key_count, abnormal_detected, input_blocked

    # 计算时间间隔
    current_timestamp = time.time()
    interval = current_timestamp - last_key_timestamp

    # 更新时间戳和按键次数
    last_key_timestamp = current_timestamp
    key_count += 1

    # 判断时间间隔内按键次数是否超过门限值
    if interval < threshold and key_count > 30:
        # 时间间隔内按键次数超过门限值
        if not input_blocked:
            input_blocked = True
            if not abnormal_detected:
                show_abnormal_input()
                abnormal_detected = True
            # 3秒后恢复正常状态
            threading.Timer(3, restore_normal_input).start()

def reset_key_count():
    global key_count
    key_count = 0

def handle_new_device(event):
    # 校验设备标识，这里假设通过设备名称进行比对
    device_name = event.name
    if is_valid_device(device_name):
        # 允许设备输入内容
        if abnormal_detected:
            show_normal_input()
            abnormal_detected = False
        input_blocked = False
    else:
        # 禁止设备输入内容
        show_abnormal_input()
        abnormal_detected = True
        input_blocked = True

def is_valid_device(device_name):
    # 假设设备名称为"ValidDevice"
    return device_name == "ValidDevice"

def show_abnormal_input():
    label.config(text="检测到异常输入", fg="red", font=("宋体", 16))

def show_normal_input():
    label.config(text="正常输入设备", fg="black", font=("宋体", 16))

def restore_normal_input():
    global abnormal_detected
    abnormal_detected = False
    if not input_blocked:
        show_normal_input()

def start_device_monitoring():
    keyboard.on_press(check_key_interval)
    keyboard.on_release(handle_new_device)

def start_gui():
    # 每秒重置按键次数
    threading.Timer(1.0, reset_key_count).start()

    # 启动GUI窗口的消息循环
    window.mainloop()

# 创建并启动设备监控线程
device_thread = threading.Thread(target=start_device_monitoring)
device_thread.daemon = True
device_thread.start()

# 启动GUI界面
start_gui()
