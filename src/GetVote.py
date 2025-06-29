import requests
import csv
import os
import time
import tempfile
import shutil
from datetime import datetime

# 使用环境变量获取凭据
username = os.environ.get('S1_USERNAME', '')  # 从环境变量获取用户名
password = os.environ.get('S1_PASSWORD', '')  # 从环境变量获取密码
login_url = "https://stage1st.com/2b/api/app/user/login"  # 替换为实际登录URL
process_url = "https://stage1st.com/2b/api/app/poll/options"  # 替换为实际处理URL

# 自定义请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

# 创建会话对象
session = requests.Session()

# 登录请求
def login():
    # 检查凭据是否设置
    if not username or not password:
        print("错误：用户名或密码未设置！")
        return None
    
    payload = {
        "username": username,
        "password": password,
        "questionid": "0",
        "answer": ""
    }
    
    try:
        # 发送登录请求（使用会话对象）
        response = session.post(
            login_url, 
            data=payload, 
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        
        # 检查登录结果
        if result.get("success") is True:
            print("✅ 登录成功")
            return result  # 返回完整响应数据
        else:
            print("❌ 登录失败")
            if "message" in result:
                print(f"原因: {result['message']}")
            return None
            
    except Exception as err:
        print(f"登录失败: {err}")
        return None

# 读取CSV文件（修改：保留原始列顺序）
def read_csv(file_path):
    rows = []
    fieldnames = []
    
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames or []
            
            # 确保所有需要的列都存在（不改变顺序）
            required_columns = [f'votes{i}' for i in range(1, 6)] + ['message']
            existing_columns = set(fieldnames)
            
            # 添加缺失的列（但不改变原有列顺序）
            for col in required_columns:
                if col not in existing_columns:
                    fieldnames.append(col)
            
            for row in reader:
                # 确保行中有所有列
                for col in required_columns:
                    if col not in row:
                        row[col] = ""  # 初始化为空字符串
                rows.append(row)
        
        return rows, fieldnames
    except Exception as err:
        print(f"读取CSV文件失败: {err}")
        return [], []

# 处理tid请求并更新行数据
def process_tid_and_update_row(sid, row, index, total):
    tid = row.get('tid', '')
    title = row.get('title', '无标题')  # 获取标题，如果没有则显示"无标题"
    
    # 显示进度信息
    print(f"[{index+1}/{total}] {title} [{tid}]")
    
    if not tid:
        print("⚠️ 跳过无TID的行")
        return row
    
    try:
        payload = {
            "sid": sid,
            "tid": tid
        }
        
        # 发送处理请求（使用会话对象）
        response = session.post(
            process_url, 
            data=payload, 
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        
        # 检查处理结果
        if result.get("success") is True:
            # 获取前5个投票选项的votes值
            data = result.get("data", [])
            
            # 初始化所有votes列为0
            for i in range(1, 6):
                row[f'votes{i}'] = 0
                row['message'] = ''  # 清空错误信息
            
            # 更新前5个选项的votes值
            for i, option in enumerate(data[:5]):
                row[f'votes{i+1}'] = option.get('votes', 0)
        else:
            # 处理失败时设置错误信息
            message = result.get("message", "未知错误")
            row['message'] = message
            
            # 重置votes列为0
            for i in range(1, 6):
                row[f'votes{i}'] = 0
            
    except requests.exceptions.HTTPError as err:
        error_msg = f"HTTP错误: {err.response.status_code}"
        row['message'] = error_msg
    except Exception as err:
        error_msg = f"请求异常: {str(err)}"
        row['message'] = error_msg
    
    return row

# 保存CSV文件（修改：不创建备份，使用安全写入方式）
def save_csv(file_path, rows, fieldnames):
    # 创建临时文件
    temp_file = None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8-sig', 
            newline='', 
            delete=False
        ) as temp:
            temp_file = temp.name
            writer = csv.DictWriter(temp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        # 用临时文件替换原文件
        shutil.move(temp_file, file_path)
        print(f"✅ 已安全更新CSV文件: {file_path}")
        return True
    except Exception as err:
        print(f"保存CSV文件失败: {err}")
        # 清理临时文件
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return False

# 主程序
if __name__ == "__main__":
    # 检查环境变量
    if not username or not password:
        print("错误：必须设置 S1_USERNAME 和 S1_PASSWORD 环境变量")
        exit(1)
    
    # 第一步：登录获取sid
    login_result = login()
    if not login_result or not login_result.get("success"):
        print("程序终止：登录失败")
        exit(1)
    
    # 第二步：从登录结果中获取sid
    sid = login_result["data"]["sid"]  # 根据实际响应结构调整
    print(f"已获取会话ID")
    
    # 第三步：读取CSV文件
    csv_file = "database.csv"  # 替换为实际文件路径
    rows, fieldnames = read_csv(csv_file)
    
    if not rows:
        print("未找到有效数据，程序终止")
        exit(1)
        
    total_rows = len(rows)
    print(f"找到 {total_rows} 行需要处理")
    print("=" * 50)
    
    # 第四步：处理每行并更新数据
    processed_count = 0
    for index, row in enumerate(rows):
        row = process_tid_and_update_row(sid, row, index, total_rows)
        processed_count += 1
        
        # 避免请求过于频繁
        time.sleep(0.5)
    
    # 第五步：保存更新后的CSV文件
    if save_csv(csv_file, rows, fieldnames):
        print(f"\n处理完成: 已更新 {total_rows} 行数据")
    else:
        print("\n处理完成但保存失败，请检查错误")
