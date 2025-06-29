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
    'username': os.environ.get('S1_USERNAME', ''),
    'password': os.environ.get('S1_PASSWORD', ''),
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
    existing_tids = set()  # 存储现有帖子的tid集合
    max_existing_tid = 0   # 现有最大tid
    existing_data = []     # 存储现有数据
    all_fieldnames = []    # 存储所有字段名
    
    if os.path.exists(output_filename):
        with open(output_filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            all_fieldnames = reader.fieldnames  # 保存所有现有字段名
            
            for row in reader:
                tid = row.get('tid')
                if tid:
                    try:
                        tid_int = int(tid)
                        existing_tids.add(tid)
                        if tid_int > max_existing_tid:
                            max_existing_tid = tid_int
                    except ValueError:
                        pass
                # 保存现有数据行
                existing_data.append(row)
                
            print(f"发现现有数据文件，包含 {len(existing_tids)} 条记录，最大tid为{max_existing_tid}")
            if all_fieldnames:
                print(f"现有字段: {', '.join(all_fieldnames)}")
    else:
        print("未发现现有数据文件，将创建新文件")
        # 如果没有文件，使用默认字段
        all_fieldnames = ['title', 'tid', 'replies', 'views', 'post_time']

    with requests.Session() as session:
        if not login(session, CONFIG['base_url'], CONFIG['username'], CONFIG['password']):
            return None, existing_tids, max_existing_tid, all_fieldnames, existing_data

        new_threads = []
        page = 1
        forum_url = f"{CONFIG['base_url']}/forum.php?mod=forumdisplay&fid={CONFIG['forum_fid']}&filter=author&orderby=dateline"
        print(f"\n开始爬取板块 (fid={CONFIG['forum_fid']})...")
        has_more_pages = True
        found_max_tid = False

        while has_more_pages and not found_max_tid:
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
                    
                    # 将tid转换为整数用于比较
                    try:
                        tid_int = int(tid)
                    except ValueError:
                        tid_int = 0
                    
                    # 如果遇到现有最大tid，停止爬取
                    if tid_int == max_existing_tid:
                        print(f"遇到现有最大tid（{max_existing_tid}），停止爬取")
                        found_max_tid = True
                        break
                    
                    # 如果是新帖子
                    if tid not in existing_tids:
                        numbers = row.select_one('td.num')
                        if numbers:
                            replies = numbers.find_all('a')[0].get_text(strip=True)
                            views = numbers.find_all('em')[0].get_text(strip=True)
                        else:
                            replies = views = ''

                        time_tag = row.select_one('td.by em span') or row.select_one('td.by em')
                        post_time = time_tag.get('title') if time_tag and time_tag.has_attr('title') else time_tag.get_text(strip=True) if time_tag else ''

                        print(f"发现新帖子 (tid={tid})，添加到数据库")
                        
                        # 创建新帖子数据，包含所有必需字段
                        new_post = {
                            'title': title,
                            'tid': tid,
                            'replies': replies,
                            'views': views,
                            'post_time': post_time
                        }
                        
                        # 添加其他字段的空值以匹配现有结构
                        for field in all_fieldnames:
                            if field not in new_post:
                                new_post[field] = ''
                        
                        new_threads.append(new_post)
                    else:
                        print(f"跳过现有帖子 (tid={tid})")

                if found_max_tid:
                    break  # 跳出外层循环

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

        return new_threads, existing_tids, max_existing_tid, all_fieldnames, existing_data

def save_to_csv(new_data, existing_data, filename, fieldnames):
    # 如果没有新数据，直接返回
    if not new_data:
        print("没有新数据可以保存。")
        return

    # 将新数据放在最前面
    combined_data = new_data + existing_data
    
    print(f"\n正在将 {len(combined_data)} 条数据保存到 {filename} ...")

    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(combined_data)
        
        print(f"数据已成功保存到 {filename}")
        print(f"新增了 {len(new_data)} 条记录，总记录数: {len(combined_data)}")
    except IOError as e:
        print(f"保存文件时出错: {e}")

if __name__ == '__main__':
    # 检查环境变量
    if not CONFIG['username'] or not CONFIG['password']:
        print("错误：必须设置 S1_USERNAME 和 S1_PASSWORD 环境变量")
        exit(1)
    
    new_threads, existing_tids, max_existing_tid, all_fieldnames, existing_data = scrape_forum()
    if new_threads is not None:
        # 按tid从大到小排序新数据（确保最新帖子在最前面）
        new_threads_sorted = sorted(
            new_threads, 
            key=lambda x: int(x['tid']), 
            reverse=True
        )
        
        # 保存所有数据到CSV文件（新数据在最前面）
        save_to_csv(new_threads_sorted, existing_data, "database.csv", all_fieldnames)
