import requests
from bs4 import BeautifulSoup
import time
import csv
import os
import re

# ====================================================================================
# 使用环境变量配置论坛信息
# ====================================================================================
CONFIG = {
    'base_url': 'https://stage1st.com/2b',
    'username': os.environ.get('S1_USERNAME', ''),  # 从环境变量获取用户名
    'password': os.environ.get('S1_PASSWORD', ''),  # 从环境变量获取密码
    'forum_fid': 83,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
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

def login(session, base_url, username, password):
    # 检查凭据是否设置
    if not username or not password:
        print("错误：用户名或密码未设置！")
        return False
    
    print("正在尝试登录...")
    login_url = f"{base_url}/member.php?mod=logging&action=login&loginsubmit=yes"
    data = {
        'username': username,
        'password': password,
        'quickforward': 'yes',
        'handlekey': 'ls'
    }
    headers = {'User-Agent': CONFIG['user_agent']}

    try:
        response = session.post(login_url, data=data, headers=headers)
        response.raise_for_status()
        if 'succeed' in response.text or username in response.text:
            print("登录成功！")
            return True
        else:
            print("登录失败！请检查用户名和密码。")
            return False
    except requests.exceptions.RequestException as e:
        print(f"登录请求发生错误: {e}")
        return False

def scrape_forum():
    # 检查现有数据文件
    output_filename = "database.csv"
    existing_dict = {}  # 存储现有帖子的字典，key为tid
    max_existing_tid = 0  # 现有最大tid
    fieldnames_list = []  # 存储所有字段名的有序列表
    
    if os.path.exists(output_filename):
        with open(output_filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # 保存原始字段名和顺序
            original_fieldnames = reader.fieldnames or []
            fieldnames_list = list(original_fieldnames)
            
            for row in reader:
                tid = row.get('tid')
                if tid:
                    # 将tid转换为整数
                    try:
                        tid_int = int(tid)
                    except ValueError:
                        tid_int = 0
                    
                    # 更新最大tid
                    if tid_int > max_existing_tid:
                        max_existing_tid = tid_int
                    
                    # 保留所有原始列数据
                    existing_dict[tid] = row
            
            print(f"发现现有数据文件，包含 {len(existing_dict)} 条记录，最大tid为{max_existing_tid}")
            if original_fieldnames:
                print(f"原始字段顺序: {', '.join(original_fieldnames)}")
    else:
        print("未发现现有数据文件，将创建新文件")
        # 基础字段顺序
        fieldnames_list = ['title', 'tid', 'replies', 'views', 'post_time']

    with requests.Session() as session:
        if not login(session, CONFIG['base_url'], CONFIG['username'], CONFIG['password']):
            return None, existing_dict, fieldnames_list

        new_threads = []
        page = 1
        forum_url = f"{CONFIG['base_url']}/forum.php?mod=forumdisplay&fid={CONFIG['forum_fid']}&filter=author&orderby=dateline"
        print(f"\n开始爬取板块 (fid={CONFIG['forum_fid']})...")
        has_more_pages = True

        while has_more_pages:
            current_page_url = f"{forum_url}&page={page}"
            print(f"正在爬取第 {page} 页...")

            headers = {'User-Agent': CONFIG['user_agent']}

            try:
                response = session.get(current_page_url, headers=headers)
                response.raise_for_status()
                response.encoding = 'utf-8'

                soup = BeautifulSoup(response.text, 'html.parser')
                thread_rows = soup.select('tbody[id^="normalthread_"]')

                if not thread_rows:
                    print("在本页未找到帖子，可能已到达最后一页。")
                    break

                for row in thread_rows:
                    title_tag = row.select_one('a.xst')
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    relative_link = title_tag['href']
                    
                    # 提取tid
                    tid = extract_tid_from_url(relative_link)
                    if not tid:
                        # 如果从相对链接提取失败，尝试完整链接
                        full_link = f"{CONFIG['base_url']}/{relative_link}"
                        tid = extract_tid_from_url(full_link)
                    
                    if not tid:
                        print(f"警告: 无法从链接中提取tid: {relative_link}")
                        continue
                    
                    # 提取回复数和浏览量
                    numbers = row.select_one('td.num')
                    if numbers:
                        replies = numbers.find_all('a')[0].get_text(strip=True)
                        views = numbers.find_all('em')[0].get_text(strip=True)
                    else:
                        replies = views = ''

                    # 提取发帖时间
                    time_tag = row.select_one('td.by em span') or row.select_one('td.by em')
                    post_time = time_tag.get('title') if time_tag and time_tag.has_attr('title') else time_tag.get_text(strip=True) if time_tag else ''
                    
                    # 将tid转换为整数用于比较
                    try:
                        tid_int = int(tid)
                    except ValueError:
                        tid_int = 0
                    
                    # 判断是否为新帖子（tid大于现有最大tid）
                    if tid_int > max_existing_tid:
                        print(f"发现新帖子 (tid={tid})，添加到数据库")
                        # 创建包含基础字段的新帖子数据
                        new_thread = {
                            'title': title,
                            'tid': tid,
                            'replies': replies,
                            'views': views,
                            'post_time': post_time
                        }
                        new_threads.append(new_thread)
                        
                        # 检查新字段是否需要添加到字段列表
                        for key in new_thread.keys():
                            if key not in fieldnames_list:
                                print(f"发现新字段 '{key}'，添加到字段列表末尾")
                                fieldnames_list.append(key)
                    else:
                        # 更新现有帖子的回复数和浏览量
                        if tid in existing_dict:
                            print(f"更新现有帖子 (tid={tid}) 的回复数和浏览量")
                            existing_dict[tid]['replies'] = replies
                            existing_dict[tid]['views'] = views

                # 检查是否有下一页
                next_page_link = soup.select_one('a.nxt')
                if not next_page_link:
                    print("未找到'下一页'按钮，爬取结束。")
                    has_more_pages = False
                else:
                    page += 1
                    time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                print(f"爬取第 {page} 页时发生错误: {e}")
                break
            except Exception as e:
                print(f"处理第 {page} 页时发生未知错误: {e}")
                break

        return new_threads, existing_dict, fieldnames_list

def save_to_csv(data, filename, fieldnames):
    if not data:
        print("没有数据可以保存。")
        return

    print(f"\n正在将 {len(data)} 条数据保存到 {filename} ...")
    print(f"字段顺序保持不变: {', '.join(fieldnames)}")

    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # 确保每条数据都有所有字段
            for row in data:
                # 创建新行，保持字段顺序
                ordered_row = {}
                for field in fieldnames:
                    # 如果字段存在，使用原值；否则设为空字符串
                    ordered_row[field] = row.get(field, '')
                writer.writerow(ordered_row)
                
        print(f"数据已成功保存到 {filename}")
    except IOError as e:
        print(f"保存文件时出错: {e}")

if __name__ == '__main__':
    # 检查环境变量是否设置
    if not CONFIG['username'] or not CONFIG['password']:
        print("错误：必须设置 S1_USERNAME 和 S1_PASSWORD 环境变量")
        exit(1)
    
    new_threads, existing_dict, fieldnames_list = scrape_forum()
    if new_threads is not None:
        # 合并数据：新数据 + 更新后的现有数据
        combined_data = list(existing_dict.values()) + new_threads
        
        # 按tid从大到小排序
        combined_data_sorted = sorted(
            combined_data, 
            key=lambda x: int(x.get('tid', 0)), 
            reverse=True
        )
        
        # 保存数据，保持原始字段顺序
        save_to_csv(combined_data_sorted, "database.csv", fieldnames_list)
