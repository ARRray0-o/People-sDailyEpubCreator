from lxml import html
from datetime import datetime, timedelta
from ebooklib import epub
import requests
import os
import re
from urllib.parse import quote
import webbrowser
from tkinter import Tk, Frame, Button, messagebox, ttk
from tkcalendar import Calendar
import threading
import base64
import tempfile

def fetch_articles(custom_date=None):
    articles_data = []
    today = custom_date if custom_date else datetime.now().strftime('%Y-%m/%d')
    date_obj = datetime.strptime(today, "%Y-%m/%d")
    if date_obj >= datetime(2024, 12, 1):
        year_month = today.replace("-", "")[:6]  # 2024-12/01 → 202412
        day = today[-2:]
        base_url = f'https://paper.people.com.cn/rmrb/pc/layout/{year_month}/{day}/'
        index_page = 'node_01.html'
    else:
        base_url = f'http://paper.people.com.cn/rmrb/html/{today}/' 
        index_page = 'nbs.D110000renmrb_01.htm'

    try:
        response = requests.get(base_url + index_page)
        response.raise_for_status()
    except requests.HTTPError:
        print('页面未找到，请确认目标日期的《人民日报》（电子版）是否已发行，或检查系统日期。')
        return articles_data, today
    except requests.RequestException as e:
        print(f'网络请求出错: {e}')
        return articles_data, today

    doc = html.fromstring(response.content)
    sections = doc.xpath('/html/body/div[2]/div[2]/div[2]/div/div/a')
    
    section_counter = 0  # 添加计数器初始化
    unique_articles = set()  # 添加去重集合初始化

    for section in sections:
        section_counter += 1
        article_counter = 0  # 每个版块重置文章计数器
        section_name = section.text_content().split('：')[-1]
        section_url = base_url + section.get('href').lstrip('./')

        try:
            response = requests.get(section_url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f'获取文章链接时出错: {e}')
            continue

        doc = html.fromstring(response.content)
        articles = doc.xpath('/html/body/div[2]/div[2]/div[3]/ul/li/a')

        for article in articles:
            article_counter += 1
            article_title = article.text_content().strip()
            article_url = base_url + article.get('href')

            try:
                response = requests.get(article_url)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f'获取文章内容时出错: {e}')
                continue

            doc = html.fromstring(response.content)
            
            article_paragraphs = doc.xpath('//div[@id="ozoom"]/p')
            article_content = ''.join([f'<p>{html.tostring(p, encoding=str, method="html", with_tail=False).strip()}</p>' for p in article_paragraphs])
            article_signature = (section_name, article_title, article_content)
            if article_signature in unique_articles:
                continue
            unique_articles.add(article_signature)
            
            filename = f'{section_counter}_{article_counter}.xhtml'
            articles_data.append((section_name, article_title, article_content, filename))

    return articles_data, today

def parse_date_input(user_input):
    current_year = datetime.now().year
    try:
        if user_input == "":
            return datetime.now().strftime('%Y-%m/%d'), False

        if user_input.startswith("-") and user_input[1:].isdigit():
            days_ago = int(user_input[1:])
            target_date = datetime.now() - timedelta(days=days_ago)
            return target_date.strftime('%Y-%m/%d'), True

        parts = user_input.split(" ")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            year = int(parts[0]) if len(parts[0]) == 4 else int("20" + parts[0])
            month = int(parts[1])
            day = int(parts[2])
        elif len(parts) == 2 and all(part.isdigit() for part in parts):
            year = current_year
            month = int(parts[0])
            day = int(parts[1])
        elif len(parts) == 1 and parts[0].isdigit():
            input_weekday = int(parts[0])
            if input_weekday < 1 or input_weekday > 7:
                raise ValueError("星期数必须在1到7之间。")
            weekday = (input_weekday - 1) % 7
            today = datetime.now()
            today_weekday = today.weekday()
            day_diff = (today_weekday - weekday) % 7
            target_date = today - timedelta(days=day_diff) if day_diff != 0 else today
            return target_date.strftime('%Y-%m/%d'), True
        else:
            raise ValueError("输入格式错误，请按照规定格式输入日期。")

        return datetime(year, month, day).strftime('%Y-%m/%d'), True
    except ValueError as e:
        return None, False

def create_epub(articles_data, today):
    book = epub.EpubBook()
    book.set_title(f'人民日报_{today.replace("/", "-")}')
    sections = {}
    spine = ['nav']
    toc = []

    for section_name, article_title, content, filename in articles_data:
        if section_name not in sections:
            sections[section_name] = {
                'section': epub.EpubHtml(title=section_name, file_name=f'{section_name}.xhtml', lang='zh', content=f'<h1>{section_name}</h1>'),
                'articles': []
            }
            book.add_item(sections[section_name]['section'])

        article_id = f'article_{filename[:-6]}'
        sub_section = epub.EpubHtml(title=article_title, file_name=filename, content=f'<h2>{article_title}</h2>{content}', lang='zh')
        sections[section_name]['articles'].append(sub_section)
        book.add_item(sub_section)

    for section_info in sections.values():
        spine.append(section_info['section'])
        toc.append((section_info['section'], section_info['articles']))
        for article in section_info['articles']:
            spine.append(article)

    book.spine = spine
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content='BODY {color: black;}'))
    epub_filename = f'人民日报_{today.replace("/", "-")}.epub'
    epub.write_epub(epub_filename, book, {})

def format_date_chinese(date):
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    year = date.year
    month = date.month
    day = date.day
    weekday = weekdays[date.weekday()]
    return f"{year}年{month}月{day}日{weekday}"

help_url = "https://flowus.cn/share/c36bef62-e964-457c-8850-369dcbfbd222"  #实际页面URL

class DatePickerApp:
    def __init__(self, master):
        self.master = master
        master.title("PDEC")
        
        self.frame = Frame(master)
        self.frame.pack(padx=20, pady=20)
        
        # 日历控件
        self.cal = Calendar(self.frame, selectmode='day', 
                          year=datetime.now().year,
                          month=datetime.now().month, 
                          day=datetime.now().day,
                          mindate=datetime(2022, 1, 1),  # 已存在的起始日期设置
                          maxdate=datetime.now(),        # 保持截止日期为当天
                          locale='zh_CN',                # 确保使用中文环境
                          date_pattern='y-mm/dd',
                          firstweekday='sunday',         # 新增周日作为每周首日
                          showweeknumbers=False)         # 隐藏周编号
        self.cal.pack(pady=10)
        
        # 操作按钮
        self.btn_frame = Frame(self.frame)
        self.btn_frame.pack(pady=10)
        
        Button(self.btn_frame, text="确定所选日期", command=self.start_download).pack(side='left', padx=5)
        Button(self.btn_frame, text="程序主页", command=lambda: webbrowser.open(help_url)).pack(side='left', padx=5)
        Button(self.btn_frame, text="退出程序", command=master.quit).pack(side='left', padx=5)
        
    
    def start_download(self, custom_date=None):
        def download_thread():
            target_date = custom_date or self.cal.get_date()
            try:
                if datetime.strptime(target_date, '%Y-%m/%d') < datetime(2022, 1, 1):
                    messagebox.showwarning("日期错误", "仅支持2022年1月1日及以后的报纸下载")
                    return
                    
                articles_data, today = fetch_articles(target_date)
                if articles_data:
                    create_epub(articles_data, today)
                    messagebox.showinfo("下载完成", 
                        f"成功生成《人民日报》{format_date_chinese(datetime.strptime(target_date, '%Y-%m/%d'))}电子版")
                else:
                    messagebox.showerror("下载失败", "页面未找到，请确认目标日期的《人民日报》（电子版）是否已发行。")
            except Exception as e:
                messagebox.showerror("发生错误", str(e))
        
        threading.Thread(target=download_thread).start()

#ico文件base64数据
ICON_DATA = b'''
AAABAAEAQEAAAAEAIAAoQgAAFgAAACgAAABAAAAAgAAAAAEAIAAAAAAAAEAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAD+/v4W/v7+XP7+/pX+/v69/v7+2f7+/uv+/v71/v7++/7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/vv+/v71/v7+6/7+/tn+/v69/v7+lf7+/lz+/v4WAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAIAAAACAAAAAgAA
AAIAAAACAAAAAv7+/jr+/v6z/v7+/f7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/f7+/rP+/v48AAAAAgAAAAIAAAACAAAAAgAAAAIAAAACAAAAAgAA
AAAAAAAAAAAAAAAAAAAAAAAA/v7+FP7+/qf+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/qf+/v4UAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/v7+LP7+/uH+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+4f7+/iwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/v7+LP7+
/u3+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/4+P3/7y87f+8vO3/vLzt/7y87f+8vO3/vLzt/7y8
7f+8vO3/vL3t/+bm+P/+/v7//v7+//7+/v/+/v7//v7+/+Lj9//MzfH/zM3x/8zN
8f/MzfH/zM3x/8zN8f/MzfH/zM3x/9XV9P/9/f7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7t/v7+LAAAAAAAAAAAAAAAAAAA
AAIAAAAC/v7+FP7+/uH+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/3t/2/wwSwP8BB77/AQe+/wEH
vv8BB77/AQe+/wEHvv8BB77/AQe+/wEHvv8QFsL/5uf4//7+/v/+/v7//f3+/2Rp
2P8BB77/AQe+/wEHvv8BB77/AQe+/wEHvv8BB77/AQe+/wEHvv8BB77/MDXK/+Xm
+P/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/uH+/v4UAAAAAgAAAAIAAAAAAAAAAP7+/qf+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/8HE
8P8CEMH/AhDB/wIQwf8CEMH/AhDB/wIQwf8CEMH/AhDB/wIQwf8CEMH/AhDB/77B
7//+/v7//v7+/6uw6v8CEMH/AhDB/wIQwf8CEMH/AhDB/wIQwf8CEMH/AhDB/wIQ
wf8CEMH/AhDB/wIQwf9eZ9j//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+pwAAAAAAAAAAAAAAAP7+/jz+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/jZTj/1xn2P9cZ9j/XGfY/1xn2P9cZ9j/XGfY/1xn
2P8kM8v/BhjE/wYYxP+9wu///v7+//7+/v98heD/BhjE/wYYxP8xP87/TFnV/0xZ
1f9MWdX/TFnV/0xZ1f9MWdX/R1PT/wYYxP8GGMT/MD/O//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v46AAAAAAAA
AAD+/v6z/v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/XW7Z/wgixf8IIsX/vsXv//7+/v/+/v7/e4ng/wgi
xf8IIsX/n6ro//7+/v/+/v7//v7+//7+/v/+/v7//v7+/+vt+v8IIsX/CCLF/zFH
zv/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+swAAAAD+/v4W/v7+/f7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/1502/8KK8n/CivJ/77H
8P/+/v7//v7+/32O4v8KK8n/CivJ/6Ct6v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/r7vr/CivJ/woryf8zTtL//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v3+/v4W/v7+XP7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v9ged3/DTLM/w0yzP+/yfH//v7+//7+/v9+kuT/DTLM/w0yzP+hsOv//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/6+76/w0yzP8NMsz/NVTU//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+XP7+
/pX+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/+vv+/+uve7/o7Ts/6O07P+jtOz/o7Ts/6O07P+jtez/pLXs/6S1
7P+ktez/pLXs/6S17P+ltu3/Q2XZ/w87zv8PO87/wMvy//7+/v/+/v7/f5fl/w87
zv8PO87/orPs//7+/v/+/v7//v7+//7+/v/+/v7//v7+/+vv+/8PO87/DzvO/zdb
1v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/pX+/v69/v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+/6q87v8ZS9L/EEPQ/xBD0P8QQ9D/EEPQ/xBD
0P8QQ9D/EEPQ/xBD0P8QQ9D/EEPQ/xBD0P8QQ9D/EEPQ/xBD0P8QQ9D/EEPQ/8DN
8v/+/v7//v7+/3+b5v8QQ9D/EEPQ/6K27f/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/r8Pv/EEPQ/xBD0P83Ytj//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v69/v7+2f7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/9rj+P8XT9X/E0vU/xNL
1P8TS9T/E0vU/xNL1P8TS9T/E0vU/xNL1P8TS9T/E0vU/xNL1P8TS9T/E0vU/xNL
1P8TS9T/E0vU/xNL1P/Q2/b//v7+//7+/v+Bn+j/E0vU/xNL1P+jue7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/7PD7/xNL1P8TS9T/Omnb//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+2f7+
/uv+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v+Kqev/FFPW/xRT1v8xZ9v/YInj/2GK4/9hiuP/YYvj/2KL4/9ii+P/Yovj/2OM
5P9jjOT/ZI3k/2SN5P9ljeT/ZY3k/2aO5P+atO3//v7+//7+/v/+/v7/gqPp/xRT
1v8UU9b/pLzv//7+/v/+/v7//v7+//7+/v/+/v7//v7+/+zx+/8UU9b/FFPW/ztv
3f/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/uv+/v71/v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/eKDo/xVb2P8VW9j/p8Hw//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/4Oo6v8VW9j/FVvY/6S/7//+/v7//v7+//7+/v/+/v7//v7+//7+
/v/s8fv/FVvY/xVb2P88dt7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v71/v7++/7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/3ik6v8WYtr/FmLa/6rG
8f/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Dq+z/FmLa/xZi2v+lwvH//v7+//7+
/v/+/v7//f3+//7+/v/+/v7/7PL8/xZi2v8WYtr/PHzh//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7++/7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v96qOv/GGnc/xhp3P+syfL//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/hK/t/xhp
3P8Yadz/psXx/+Pj/v/MzP7/zMz+/7Cw/v/8/P7//v7+/+zz/P8Yadz/GGnc/z+C
4v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/e6zs/xtw3v8bcN7/rcvz//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/4az7f8bcN7/G3De/6fH8v/+/v7/8fH+//7+/v/f3/7//v7+//7+
/v/s8/z/G3De/xtw3v9Bh+P//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/3uv7f8cdd//HHXf/63O
8//+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Gtu7/HHXf/xx13/+Ou+//1uf5/9bn
+f/W5/n/1uf5/9bn+f/W5/n/x973/xx13/8cdd//QYzl//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v99tO//Hn3k/x595P+u0PX//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/ksDy/x59
5P8efeT/Hn3k/x595P8efeT/Hn3k/x595P8efeT/Hn3k/x595P8efeT/Hn3k/06Z
6v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/fbfw/x6C5f8eguX/r9L1//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/+Dt+/8oiOb/HoLl/x6C5f8eguX/HoLl/x6C5f8eguX/HoLl/x6C
5f8eguX/HoLl/x6C5f+mzfT//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/3+78P8hieb/IYnm/7DV
9v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/1Oj6/2+y7/9ap+z/Wqft/1qn
7f9ap+3/Wqft/1qn7f9ap+3/Wqft/2Kr7f+u1Pb//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v9/vvL/IY7p/yGO6f+w1/f/w8P+/46O/v/5+f7//v7+/8XF/v99ff7/+Pj+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Jif7/sbH+/6Wl/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/f8Hz/yGU6/8hlOv/sdn4//7+/v/Ozv7/eXn+//7+
/v9kZP7/xMT+/+Li/v/m5v7/9PT+/+fn/v/+/v7//v7+//7+/v/+/v7//v7+/4qK
/v9AQP7/pqb+/+/v/v+MjP7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/4HE9P8lme3/JZnt/7Pb
+P/+/v7//v7+/3l5/v/Hx/7/xcX+//7+/v/+/v7/m5v+/3Fx/v8/P/7//f3+//Ly
/v9hYf7/cnL+//7+/v/+/v7/bGz+/6io/v+IiP7/xMT+//7+/v/+/v7//v7+//7+
/v/w+P3/gcX1/5TO9//9/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v+Bx/X/JJ7u/ySe7v+z3fn//v7+//7+/v/e3v7/cnL+//7+/v/+/v7//v7+/8rK
/v90dP7/qan+//7+/v/6+v7/MzP+/0dH/v/+/v7//v7+/5GR/v9paf7/mZn+/8XF
/v/+/v7//v7+//7+/v/+/v7/j832/ySe7v8knu7/weP6//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/gsr1/yaj7v8mo+7/tN/5//7+/v/+/v7//v7+/1NT
/v/x8f7//v7+//7+/v/9/f7/k5P+/4mJ/v/+/v7//v7+/6ys/v9ERP7//v7+//7+
/v+0tP7/qan+/4yM/v+jo/7/t7f+//7+/v/+/v7//v7+/4TL9f8mo+7/JqPu/7Tf
+f/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/4LM9v8nqPD/J6jw/7Th
+v/+/v7//v7+//7+/v+jo/7/lpb+//7+/v/+/v7//v7+/7y8/v9MTP7/8vL+//7+
/v/+/v7/9PT+//7+/v/+/v7/ubn+/y0t/v+cnP7/09P+//39/v/+/v7//v7+//7+
/v+Ezfb/J6jw/yeo8P+04fr//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v+Dz/f/KKzy/yis8v+14vr//v7+//7+/v/+/v7/8vL+/0VF/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/6qq/v83N/7/j4/+/2dn
/v/+/v7//v7+//7+/v/+/v7/hc/3/yis8v8orPL/teL6//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/g9H4/yiv8/8or/P/tuT7//7+/v/+/v7//v7+//7+
/v9vb/7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7/pKT+/5GR/v/q6v7//v7+//7+/v/+/v7//v7+/4XS+P8or/P/KK/z/7Xj
+//+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+/4TT+f8qs/X/KrP1/7bl
+//+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//z8/v+0tP7//v7+//7+/v/+/v7//v7+//7+
/v+F0/n/KrP1/yqz9f+15fv//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v+X3Pr/LLj1/yy49f9Wxvf/idj6/4nY+v+J2Pr/idj6/4nY+v+J2Pr/idj6/4nY
+v+J2Pr/idj6/4nY+v+J2Pr/idj6/4nY+v+J2Pr/idj6/4nY+v+J2Pr/idj6/4nY
+v+J2Pr/idj6/4nY+v+J1/r/Qb/2/yy49f8suPX/yOz8//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/4PX9/zG99/8su/f/LLv3/yy79/8su/f/LLv3/yy7
9/8su/f/LLv3/yy79/8su/f/LLv3/yy79/8su/f/LLv3/yy79/8su/f/LLv3/yy7
9/8su/f/LLv3/yy79/8su/f/LLv3/yy79/8su/f/LLv3/yy79/8su/f/SMT4//r9
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+56fz/OML3/y2+
9v8tvvb/Lb72/y2+9v8tvvb/Lb72/y2+9v8tvvb/Lb72/y2+9v8tvvb/Lb72/y2+
9v8tvvb/Lb72/y2+9v8tvvb/Lb72/y2+9v8tvvb/Lb72/y2+9v8tvvb/Lb72/y2+
9v8tvvb/Scf3/9nz/f/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//H6/v++6/z/tOj8/7To/P+06Pz/tOj8/7To/P+06Pz/tOj8/7To
/P+06Pz/tOj8/7To/P+06Pz/tOj8/7To/P+n5Pv/peT7/7To/P+06Pz/tOj8/7To
/P+06Pz/tOj8/7To/P+06Pz/xu38//n9/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/u+v7/WdD7/1bP
+//r+f7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7/keD8/4je/P+I3vz/jN/8//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/i9/7/l+T8/5Li/P+i5v3/nuX9/5Pj/P+W4/z/3/b+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/v+/7/UtP8/7Lr/f/C7/7/qen9/6To
/f/D8P7/tOz9/1LT/P/r+v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/xPD+/4rh
/f/+/v7//v7+/6zq/f+m6P3//v7+//7+/v+Q4/3/ve7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/+36/v9T1P3/we/+//z+/v/z/P7/8vv+//3+/v/D8P7/VNT9/+j5
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/2/b+/1jW/v/X9f7//v7+//7+
/v/d9v7/VNX+/9f1/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v+t6/7/hOL+//3+/v/+/v7/ieP+/6bp/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//f7+/4zk/v9S1v7/Utb+/4fj/v/8/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/+rq/v+trf7/qan+/6mp/v+pqf7/qan+/6mp/v+pqf7/paj+/6Wo
/v+pqf7/qan+/6mp/v+pqf7/qan+/6mp/v+qqv7/6en+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+/9/f/v8YGP7/TU3+/1VV/v9VVf7/VVX+/1VV
/v9VVf7/VVX+/1VV/v9VVf7/VVX+/1VV/v9VVf7/VVX+/y8v/v8ODv7/TEz+/xgY
/v/h4f7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/vv+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Pj/7/ZWX+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v9mZv7/iYn+//7+/v9gYP7/kpL+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/vv+/v71/v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7/iYn+/3Jy/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7/YGD+/5aW/v/+/v7/bGz+/4yM/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v71/v7+6/7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+/4mJ/v9wcP7/tbX+/+fn/v/Kyv7/q6v+//7+
/v/+/v7//v7+//7+/v/z8/7/np7+/8LC/v/6+v7//Pz+/2Bg/v+Wlv7//v7+/2xs
/v+MjP7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+6/7+
/tn+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Jif7/cnL+//7+
/v+Wlv7/urr+//7+/v+zs/7/np7+/+vr/v++vv7/ysr+/+Pj/v+AgP7/h4f+/+Dg
/v9gYP7/lpb+//7+/v9sbP7/jIz+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/tn+/v69/v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7/iYn+/3Jy/v/+/v7/tbX+/9jY/v/+/v7/1dX+/46O/v/6+v7/kJD+/5GR
/v/+/v7/b2/+/7Ky/v/ExP7/YGD+/5aW/v/+/v7/bGz+/4yM/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v69/v7+lf7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+/4mJ/v9ycv7//v7+//v7/v+IiP7//v7+//n5
/v+AgP7/7e3+//b2/v/U1P7//v7+/35+/v+amv7/6en+/2Bg/v+Wlv7//v7+/2xs
/v+MjP7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+lf7+
/lz+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Jif7/cnL+//7+
/v/+/v7/hob+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Zmf7/eHj+/+Li
/v9gYP7/lpb+//7+/v9sbP7/jIz+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/lz+/v4W/v7+/f7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7/iYn+/3Jy/v/+/v7//v7+//v7/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+/8vL/v/+/v7/YGD+/5GR/v/29v7/ZWX+/42N/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v3+/v4WAAAAAP7+/rP+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+/4mJ/v9ycv7//f3+/+Hh/v/h4f7/4eH+/+Hh
/v/h4f7/4eH+/+Hh/v/h4f7/4eH+/+Hh/v/i4v7//v7+/2Bg/v8GBv7/Cgr+/x0d
/v/T0/7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v6zAAAAAAAA
AAD+/v46/v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v+Jif7/cnL+/8rK
/v8fH/7/Hh7+/x4e/v8eHv7/Hh7+/x4e/v8eHv7/Hh7+/x4e/v8eHv7/Hx/+/9PT
/v9gYP7/lpb+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+PAAAAAAAAAACAAAAAv7+/qf+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7/iYn+/2pq/v/19f7/9fX+//X1/v/19f7/9fX+//X1/v/19f7/9fX+//X1
/v/19f7/9fX+//X1/v/19f7/WFj+/5eX/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+pwAAAAIAAAACAAAAAAAAAAD+/v4U/v7+4f7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+/9HR/v8eHv7/DAz+/wwM/v8MDP7/DAz+/wwM
/v8MDP7/DAz+/wwM/v8MDP7/DAz+/wwM/v8MDP7/DAz+/yIi/v/a2v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+4f7+/hQAAAACAAAAAAAA
AAAAAAAAAAAAAP7+/iz+/v7t/v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+7f7+
/i4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/v7+LP7+/uH+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+4f7+/iwAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAIAAAACAAAAAgAA
AAL+/v4U/v7+p/7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+p/7+/hQAAAACAAAAAgAAAAIAAAACAAAAAgAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD+/v48/v7+s/7+/v3+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v3+/v6z/v7+PAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAD+/v4W/v7+XP7+/pX+/v69/v7+2f7+/uv+/v71/v7++/7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+
/v/+/v7//v7+//7+/vv+/v71/v7+6/7+/tn+/v69/v7+lf7+/lz+/v4WAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/+AAAAAAB///AAAAAAAA//wA
AAAAAAA/+AAAAAAAAB/wAAAAAAAAD+AAAAAAAAAHwAAAAAAAAAPAAAAAAAAAA4AA
AAAAAAABgAAAAAAAAAGAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAABgAAAAAAAAAGAAAAAAAAAAcAA
AAAAAAADwAAAAAAAAAPgAAAAAAAAB/AAAAAAAAAP+AAAAAAAAB/8AAAAAAAAP/8A
AAAAAAD//+AAAAAAB/8=
'''

if __name__ == '__main__':
    root = Tk()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ico') as tmp_icon:
        tmp_icon.write(base64.b64decode(ICON_DATA))
        root.iconbitmap(tmp_icon.name)
    root.style = ttk.Style()
    root.style.theme_use('clam')
    app = DatePickerApp(root)
    root.mainloop()
