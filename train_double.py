import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score

# 读取数据
data = pd.read_csv('data.csv')

# 提取特征和标签
features = data.iloc[:, 2:-1]  # 选择红球的列作为特征
labels = data.iloc[:, -1]  # 选择蓝球的列作为标签

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)

# 构建决策树模型
model = DecisionTreeClassifier()

# 训练模型
model.fit(X_train, y_train)

# 在测试集上进行预测
predictions = model.predict(X_test)

# 计算准确度
accuracy = accuracy_score(y_test, predictions)
print(f'模型准确度: {accuracy}')

# 定义奖励函数
def calculate_reward(predicted_numbers, actual_numbers):
    # 这里假设 predicted_numbers 和 actual_numbers 是列表，分别包含红球和蓝球的预测和实际号码
    # 实际应根据你的数据结构进行调整
    if set(predicted_numbers[:6]) == set(actual_numbers[:6]) and predicted_numbers[6] == actual_numbers[6]:
        return 7000000  # 一等奖
    elif set(predicted_numbers[:6]) == set(actual_numbers[:6]):
        return 180000  # 二等奖
    elif len(set(predicted_numbers[:6]).intersection(set(actual_numbers[:6]))) == 5 and predicted_numbers[6] == actual_numbers[6]:
        return 3000  # 三等奖
    elif len(set(predicted_numbers[:6]).intersection(set(actual_numbers[:6]))) == 5 or (len(set(predicted_numbers[:6]).intersection(set(actual_numbers[:6]))) == 4 and predicted_numbers[6] == actual_numbers[6]):
        return 200  # 四等奖
    elif len(set(predicted_numbers[:6]).intersection(set(actual_numbers[:6]))) == 4 or (len(set(predicted_numbers[:6]).intersection(set(actual_numbers[:6]))) == 3 and predicted_numbers[6] == actual_numbers[6]):
        return 10  # 五等奖
    elif len(set(predicted_numbers[:6]).intersection(set(actual_numbers[:6]))) == 2 and predicted_numbers[6] == actual_numbers[6]:
        return 5  # 六等奖
    elif len(set(predicted_numbers[:6]).intersection(set(actual_numbers[:6]))) == 1 and predicted_numbers[6] == actual_numbers[6]:
        return 5  # 六等奖
    elif predicted_numbers[6] == actual_numbers[6]:
        return 5  # 六等奖
    else:
        return 0  # 未中奖

# 示例调用奖励函数
predicted_numbers = model.predict([X_test.iloc[0, :]])
actual_numbers = y_test.iloc[0, :]
reward = calculate_reward(predicted_numbers, actual_numbers)
print(f'中奖金额: {reward} 元')
