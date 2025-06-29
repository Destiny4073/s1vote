import csv
import math

def calculate_score(row):
    """根据投票数据计算分数"""
    # 提取各选项票数
    v1 = int(row['votes1'])
    v2 = int(row['votes2'])
    v3 = int(row['votes3'])
    v4 = int(row['votes4'])
    v5 = int(row['votes5'])
    
    # 计算原始总分
    raw_score = 2*v1 + v2 - v4 - 2*v5
    
    # 计算总票数
    total_votes = v1 + v2 + v3 + v4 + v5
    
    # 避免除零错误
    if total_votes == 0:
        return "0.0000"
    
    # 计算平均分并映射到[-200,200]范围
    average_score = raw_score / total_votes
    score_value = 100 * average_score
    
    # 格式化分数为4位小数
    score_formatted = "{:.4f}".format(score_value)
    
    return score_formatted

def calculate_std_dev(row):
    """计算基于评分分布的总体标准差"""
    # 提取各选项票数
    v1 = int(row['votes1'])
    v2 = int(row['votes2'])
    v3 = int(row['votes3'])
    v4 = int(row['votes4'])
    v5 = int(row['votes5'])
    votes = [v1, v2, v3, v4, v5]
    
    # 计算总票数
    total_votes = sum(votes)
    
    # 避免除零错误
    if total_votes == 0:
        return "0.0000"
    
    # 计算加权总分 (1*v1 + 2*v2 + ... + 5*v5)
    weighted_sum = sum((i + 1) * v for i, v in enumerate(votes))
    
    # 计算平均评分
    mean_rating = weighted_sum / total_votes
    
    # 计算方差
    variance = sum(v * ((rating + 1) - mean_rating) ** 2 
                for rating, v in enumerate(votes)) / total_votes
    
    # 计算标准差并保留4位小数
    std_dev = math.sqrt(variance)
    std_dev_formatted = "{:.4f}".format(std_dev)
    
    return std_dev_formatted

# 源文件名
source_filename = 'database.csv'

# 读取所有数据到内存
rows = []
with open(source_filename, 'r', encoding='utf-8-sig') as infile:
    reader = csv.DictReader(infile)
    original_fieldnames = reader.fieldnames  # 保存原始列顺序
    
    # 检查是否已有score列和standard_deviation列
    has_score = 'score' in original_fieldnames
    has_std_dev = 'standard_deviation' in original_fieldnames
    
    # 处理每一行
    for row in reader:
        # 计算分数
        score_formatted = calculate_score(row)
        
        # 如果已有score列，则覆盖数据
        if has_score:
            row['score'] = score_formatted
        # 否则添加新列
        else:
            row['score'] = score_formatted
        
        # 计算标准差
        std_dev_formatted = calculate_std_dev(row)
        
        # 如果已有standard_deviation列，则覆盖数据
        if has_std_dev:
            row['standard_deviation'] = std_dev_formatted
        # 否则添加新列
        else:
            row['standard_deviation'] = std_dev_formatted
        
        rows.append(row)

# 覆盖写回源文件
with open(source_filename, 'w', encoding='utf-8-sig', newline='') as outfile:
    # 准备字段名列表，保持原始顺序
    fieldnames = original_fieldnames.copy()
    
    # 如果没有score列，添加到末尾
    if not has_score and 'score' not in fieldnames:
        fieldnames.append('score')
    
    # 如果没有standard_deviation列，添加到末尾
    if not has_std_dev and 'standard_deviation' not in fieldnames:
        fieldnames.append('standard_deviation')
    
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"计算完成！已处理 {len(rows)} 条记录")
if has_score:
    print("已覆盖原有score列的数据")
else:
    print("已在文件末尾添加score列")
    
if has_std_dev:
    print("已覆盖原有standard_deviation列的数据")
else:
    print("已在文件末尾添加standard_deviation列")
