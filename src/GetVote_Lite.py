import requests
from bs4 import BeautifulSoup
import time
import re
import csv
import os
from datetime import datetime, timedelta
import tempfile

# ====================================================================================
# 使用环境变量配置信息
# ====================================================================================
CONFIG = {
    'base_url': 'https://stage1st.com/2b',
    'username': os.environ.get('S1_USERNAME', ''),
    'password': os.environ.get('S1_PASSWORD', ''),
    'forum_fid': 83,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'api_login': 'https://stage1st.com/2b/api/app/user/login',
    'api_poll': 'https://stage1st.com/2b/api/app/poll/options',
    'csv_file': 'database.csv'
}

HEADERS = {
    "User-Agent": CONFIG['user_agent'],
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}
# ====================================================================================

def extract_tid_from_url(url):
    """从URL中提取帖子ID(tid)"""
    match = re.search(r'thread-(\d+)', url)
    if match:
        return match.group(1)
    match = re.search(r'tid=(\d+)', url)
    if match:
        return match.group(1)
    return None

def login_forum(session):
    """登录论坛获取会话"""
    # 检查凭据是否设置
    if not CONFIG['username'] or not CONFIG['password']:
        print("错误：用户名或密码未设置！")
        return False
    
    print("正在尝试登录论坛...")
    login_url = f"{CONFIG['base_url']}/member.php?mod=logging&action=login&loginsubmit=yes"
    data = {
        'username': CONFIG['username'],
        'password': CONFIG['password'],
        'quickforward': 'yes',
        'handlekey': 'ls'
    }
    headers = {'User-Agent': CONFIG['user_agent']}

    try:
        response = session.post(login_url, data=data, headers=headers)
        response.raise_for_status()
        if 'succeed' in response.text or CONFIG['username'] in response.text:
            print("论坛登录成功！")
            return True
        else:
            print("论坛登录失败！请检查用户名和密码。")
            return False
    except requests.exceptions.RequestException as e:
        print(f"论坛登录请求发生错误: {e}")
        return False

def login_api(session):
    """登录API获取sid"""
    # 检查凭据是否设置
    if not CONFIG['username'] or not CONFIG['password']:
        print("错误：用户名或密码未设置！")
        return None
    
    print("正在尝试登录API...")
    payload = {
        "username": CONFIG['username'],
        "password": CONFIG['password'],
        "questionid": "0",
        "answer": ""
    }
    
    try:
        response = session.post(
            CONFIG['api_login'], 
            data=payload, 
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            print("✅ API登录成功")
            return result['data']['sid']
        else:
            print("❌ API登录失败")
            if "message" in result:
                print(f"原因: {result['message']}")
            return None
    except Exception as err:
        print(f"API登录失败: {err}")
        return None

def scrape_threads(session):
    """爬取论坛帖子（修复：根据提供的HTML结构提取最后回复时间）"""
    all_threads = []
    page = 1
    forum_url = f"{CONFIG['base_url']}/forum.php?mod=forumdisplay&fid={CONFIG['forum_fid']}&filter=lastpost&orderby=lastpost"
    print(f"\n开始爬取板块 (fid={CONFIG['forum_fid']})，按最后回复时间排序...")
    
    first_post_time = None
    stop_crawling = False
    
    while not stop_crawling:
        current_page_url = f"{forum_url}&page={page}"
        print(f"正在爬取第 {page} 页...")

        try:
            response = session.get(current_page_url, headers={'User-Agent': CONFIG['user_agent']})
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')
            thread_rows = soup.select('tbody[id^="normalthread_"]')

            if not thread_rows:
                print("在本页未找到帖子，可能已到达最后一页。")
                break

            for row in thread_rows:
                link_tag = row.select_one('a.xst')
                if not link_tag:
                    continue

                relative_link = link_tag['href']
                tid = extract_tid_from_url(relative_link) or extract_tid_from_url(f"{CONFIG['base_url']}/{relative_link}")
                
                if not tid:
                    print(f"警告: 无法从链接中提取tid: {relative_link}")
                    continue
                
                # 修改开始：定位第二个td.by元素（最后回复时间）
                by_cells = row.select('td.by')
                if len(by_cells) >= 2:  # 确保存在第二个td.by
                    last_reply_cell = by_cells[1]  # 第二个td.by包含最后回复时间
                    
                    # 提取时间 - 优先从em > a标签获取
                    time_link = last_reply_cell.select_one('em a')
                    if time_link:
                        last_reply_time_str = time_link.get_text(strip=True)
                    else:
                        # 次选：从em标签直接获取
                        em_tag = last_reply_cell.select_one('em')
                        last_reply_time_str = em_tag.get_text(strip=True) if em_tag else ''
                else:
                    last_reply_time_str = ''
                # 修改结束
                
                # 尝试解析时间字符串
                try:
                    # 移除时间字符串中可能存在的非标准字符
                    clean_time_str = re.sub(r'[^\d\-: ]', '', last_reply_time_str).strip()
                    
                    # 尝试不同的时间格式
                    try:
                        last_reply_time = datetime.strptime(clean_time_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        try:
                            # 尝试没有前导零的格式 (如2025-6-28)
                            last_reply_time = datetime.strptime(clean_time_str, '%Y-%-m-%-d %H:%M')
                        except ValueError:
                            # 尝试只有日期的情况
                            last_reply_time = datetime.strptime(clean_time_str, '%Y-%m-%d')
                except (ValueError, TypeError):
                    # 如果解析失败，使用当前时间作为备选
                    last_reply_time = datetime.now()
                    print(f"警告: 无法解析时间 '{last_reply_time_str}'，使用当前时间代替")
                
                if first_post_time is None:
                    first_post_time = last_reply_time
                    print(f"设置基准时间: {first_post_time.strftime('%Y-%m-%d %H:%M')}")
                
                time_diff = (first_post_time - last_reply_time).total_seconds() / 3600
                
                if time_diff > 24:
                    print(f"帖子 tid={tid} 最后回复时间 {last_reply_time.strftime('%Y-%m-%d %H:%M')} 与基准时间相差 {time_diff:.1f} 小时，超过24小时，停止爬取")
                    stop_crawling = True
                    break
                
                all_threads.append(tid)
                print(f"爬取到帖子: tid={tid} (最后回复: {last_reply_time_str})")

            if stop_crawling:
                break
                
            next_page_link = soup.select_one('a.nxt')
            if not next_page_link:
                break
                
            page += 1
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"爬取第 {page} 页时发生错误: {e}")
            break
        except Exception as e:
            print(f"处理第 {page} 页时发生未知错误: {e}")
            break

    print(f"共爬取 {len(all_threads)} 个帖子")
    return all_threads

def get_poll_data(session, sid, tid):
    """获取投票数据"""
    try:
        payload = {
            "sid": sid,
            "tid": tid
        }
        
        response = session.post(
            CONFIG['api_poll'], 
            data=payload, 
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            data = result.get("data", [])
            votes = [option.get('votes', 0) for option in data[:5]]
            return votes, None
        else:
            return None, result.get("message", "未知错误")
            
    except requests.exceptions.HTTPError as err:
        return None, f"HTTP错误: {err.response.status_code}"
    except Exception as err:
        return None, f"请求异常: {str(err)}"

def read_csv(file_path):
    """读取CSV文件，返回行数据和列名"""
    rows = []
    fieldnames = []
    
    try:
        if not os.path.exists(file_path):
            print(f"CSV文件不存在: {file_path}")
            return [], []
        
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames or []
            
            # 添加缺失的列
            for i in range(1, 6):
                col_name = f'votes{i}'
                if col_name not in fieldnames:
                    fieldnames.append(col_name)
            
            if 'message' not in fieldnames:
                fieldnames.append('message')
            
            for row in reader:
                rows.append(row)
        
        return rows, fieldnames
    except Exception as err:
        print(f"读取CSV文件失败: {err}")
        return [], []

def save_csv(file_path, rows, fieldnames):
    """安全保存CSV文件（使用临时文件）"""
    # 创建临时文件
    temp_file = None
    try:
        # 在相同目录创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8-sig', 
            newline='', 
            dir=os.path.dirname(file_path) or '.', 
            delete=False
        ) as temp:
            temp_file = temp.name
            
            # 写入数据到临时文件
            writer = csv.DictWriter(temp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        # 替换原文件
        os.replace(temp_file, file_path)
        print(f"✅ 已安全保存更新后的CSV文件: {file_path}")
        return True
    except Exception as err:
        print(f"保存CSV文件失败: {err}")
        # 清理临时文件
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        return False

def update_csv_with_poll_results(poll_results):
    """将投票结果更新到CSV文件"""
    csv_file = CONFIG['csv_file']
    print(f"\n开始更新CSV文件: {csv_file}")
    
    # 读取CSV文件
    rows, fieldnames = read_csv(csv_file)
    if not rows:
        print("CSV文件中无数据，无需更新。")
        return
    
    # 创建tid到投票结果的映射
    tid_to_result = {result['tid']: result for result in poll_results}
    updated_count = 0
    
    # 更新行数据
    for row in rows:
        tid = row.get('tid')
        if tid and tid in tid_to_result:
            result = tid_to_result[tid]
            
            # 重置votes列为0
            for i in range(1, 6):
                row[f'votes{i}'] = 0
            
            if result['votes']:
                # 更新投票数据
                votes = result['votes']
                for i in range(min(len(votes), 5)):
                    row[f'votes{i+1}'] = votes[i]
                row['message'] = ''  # 清空错误信息
            else:
                # 处理失败
                row['message'] = result['error'] or '未知错误'
            
            updated_count += 1
    
    # 保存更新后的CSV
    if save_csv(csv_file, rows, fieldnames):
        print(f"成功更新 {updated_count} 行数据")
    else:
        print("更新CSV文件失败")

def main():
    # 检查环境变量
    if not CONFIG['username'] or not CONFIG['password']:
        print("错误：必须设置 S1_USERNAME 和 S1_PASSWORD 环境变量")
        exit(1)
    
    with requests.Session() as session:
        # 第一步：登录论坛
        if not login_forum(session):
            return
        
        # 第二步：爬取帖子tid列表
        tids = scrape_threads(session)
        if not tids:
            print("没有找到可处理的帖子")
            return
        
        # 第三步：登录API获取sid
        sid = login_api(session)
        if not sid:
            return
        
        print("\n开始处理投票数据...")
        print("=" * 50)
        
        # 第四步：处理每个tid
        poll_results = []
        for index, tid in enumerate(tids):
            print(f"[{index+1}/{len(tids)}] 处理 tid={tid}")
            
            votes, error = get_poll_data(session, sid, tid)
            if votes:
                poll_results.append({
                    'tid': tid,
                    'votes': votes,
                    'error': None
                })
            else:
                poll_results.append({
                    'tid': tid,
                    'votes': None,
                    'error': error
                })
                print(f"处理失败: {error}")
            
            time.sleep(0.5)

        # 第五步：将数据写回CSV文件
        update_csv_with_poll_results(poll_results)

if __name__ == '__main__':
    main()
