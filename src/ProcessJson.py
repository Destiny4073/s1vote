import csv
import re
import os
import json
import datetime
import time

def process_title(title):
    """处理标题字段，提取年份、月份、类别、集数和纯标题"""
    # 改进后的正则表达式，支持单数字月份
    pattern = r'\[(\d{4})\.(\d{1,2})\]\s*\[([^\.]+)\.(\d+)\]\s*([^／/]+)'
    match = re.match(pattern, title)
    
    if match:
        year = match.group(1)
        # 处理月份：去掉前导零，保留单数字月份
        month = match.group(2).lstrip('0')
        month = month if month != '' else '0'  # 处理"00"变为"0"的情况
        
        category = match.group(3)
        
        # 处理集数：去掉前导零
        ep = match.group(4).lstrip('0')
        ep = ep if ep != '' else '0'  # 处理"00"变为"0"的情况
        
        pure_title = match.group(5).strip()  # 去掉前后空格
        
        return pure_title, '', year, month, category, ep  # 添加空别名
    return title, '', '', '', '', ''  # 如果匹配失败返回原始值

def process_csv_file(input_file):
    """处理整个CSV文件并覆盖原文件，然后另存为JSON"""
    # 读取输入CSV
    rows = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if not rows:
        print("CSV文件为空")
        return
    
    # 获取列索引
    header = rows[0]
    title_idx = header.index('title')
    
    # 检查是否已有别名等列
    required_cols = ['aliases', 'year', 'month', 'category', 'ep']
    has_all_cols = all(col in header for col in required_cols)
    
    # 创建新标题行 - 只在需要时添加新列
    if not has_all_cols:
        # 在title列后添加新列
        new_header = (
            header[:title_idx+1] + 
            required_cols + 
            header[title_idx+1:]
        )
        
        # 更新数据行，为每行添加五个空值
        for i in range(1, len(rows)):
            rows[i] = (
                rows[i][:title_idx+1] + 
                ['', '', '', '', ''] +  # 五个空值对应五个新列
                rows[i][title_idx+1:]
            )
    else:
        # 如果已有这些列，保持原样
        new_header = header
    
    # 获取新列的索引
    col_indices = {}
    for col in required_cols:
        col_indices[col] = new_header.index(col) if col in new_header else -1
    
    title_idx = new_header.index('title')  # 更新title索引位置
    
    # 处理数据行
    processed_rows = []
    for row in rows[1:]:
        # 只有当year列为空时才处理标题
        if col_indices['year'] != -1 and row[col_indices['year']] == '':
            # 处理title字段
            processed_title, aliases, year, month, category, ep = process_title(row[title_idx])
            
            # 更新纯标题
            row[title_idx] = processed_title
            
            # 更新新列的值
            if col_indices['aliases'] != -1: row[col_indices['aliases']] = aliases
            if col_indices['year'] != -1: row[col_indices['year']] = year
            if col_indices['month'] != -1: row[col_indices['month']] = month
            if col_indices['category'] != -1: row[col_indices['category']] = category
            if col_indices['ep'] != -1: row[col_indices['ep']] = ep
        
        processed_rows.append(row)
    
    # 创建临时文件路径
    temp_file = input_file + '.tmp'
    
    # 写入处理后的数据到临时文件
    with open(temp_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(new_header)
        writer.writerows(processed_rows)
    
    # 替换原文件
    os.replace(temp_file, input_file)
    print(f"文件处理完成，已覆盖原文件: {input_file}")
    
    # 构建JSON数据
    json_data = []
    
    # 将处理后的行转换为字典列表
    for row in processed_rows:
        row_dict = dict(zip(new_header, row))
        
        # 处理aliases字段 - 按分号分割并去除空格
        if 'aliases' in row_dict and row_dict['aliases']:
            aliases_str = row_dict['aliases']
            # 分割并清理每个别名
            aliases_list = [alias.strip() for alias in aliases_str.split(';') if alias.strip()]
            row_dict['aliases'] = aliases_list
        else:
            row_dict['aliases'] = []  # 确保总是数组类型
        
        json_data.append(row_dict)
    
    # 获取当前时间戳（秒级）
    current_timestamp = int(time.time())
    
    # 创建包含时间戳和数据的JSON对象
    final_json = {
        "update_time": current_timestamp,
        "data": json_data
    }
    
    # 固定JSON文件名
    # json_filename = 'database.json'
    min_json_filename = 'database.min.json'
    
    # 写入格式化的JSON文件
    # with open(json_filename, 'w', encoding='utf-8') as f:
        # json.dump(final_json, f, ensure_ascii=False, indent=2)
    
    # 写入压缩版JSON文件（无缩进/空格）
    with open(min_json_filename, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, separators=(',', ':'))
    
    # print(f"已将处理后的数据保存为JSON文件: {json_filename}")
    print(f"已生成压缩版JSON文件: {min_json_filename}")
    print(f"更新时间戳: {current_timestamp} ({datetime.datetime.fromtimestamp(current_timestamp).isoformat()})")

# 主程序
if __name__ == "__main__":
    # 输入文件路径
    input_file = 'database.csv'
    
    # 处理CSV文件
    process_csv_file(input_file)
