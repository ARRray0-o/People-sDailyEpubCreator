from lxml import html
from datetime import datetime, timedelta
from ebooklib import epub
import requests
import os
import re
from urllib.parse import quote
import webbrowser

def fetch_articles(custom_date=None):
    articles_data = []
    today = custom_date if custom_date else datetime.now().strftime('%Y-%m/%d')
    base_url = f'http://paper.people.com.cn/rmrb/html/{today}/'
    section_counter = 0
    unique_articles = set()
    
    try:
        response = requests.get(base_url + 'nbs.D110000renmrb_01.htm')
        response.raise_for_status()
    except requests.HTTPError:
        print('页面未找到，请确认目标日期的《人民日报》（电子版）是否已发行，或检查系统日期。')
        return articles_data, today
    except requests.RequestException as e:
        print(f'网络请求出错: {e}')
        return articles_data, today

    doc = html.fromstring(response.content)
    sections = doc.xpath('/html/body/div[2]/div[2]/div[2]/div/div/a')

    for section in sections:
        section_counter += 1
        article_counter = 0
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

if __name__ == '__main__':
    guide_url = "https://flowus.cn/share/c70a84fe-a3ba-450d-ba13-7e4ee855545b"
    help_url = "https://flowus.cn/pdec/2a91874c-fec4-43a2-8b1d-cbfc27720db1"
    first_run = True

    while True:
        if first_run:
            prompt_message = "本工具作为一个开源项目在GPL-3.0许可下发布,输入g后回车打开说明网页。\n请输入需要获取的报纸所发行的日期:"
            first_run = False
        else:
            prompt_message = "\n请输入需要获取的报纸所发行的日期:"

        user_input = input(prompt_message).lower()

        if user_input == 'g':
            webbrowser.open(guide_url)
            print("正在打开说明网页...")
            continue

        if user_input in ['help', 'h']:
            webbrowser.open(help_url)
            print("正在打开使用帮助...")
            continue

        target_date, need_confirmation = parse_date_input(user_input)

        while target_date is None:
            print("无法识别输入内容,请重新输入。输入help后回车打开使用帮助。")
            user_input = input("\n请输入需要获取的报纸所发行的日期:").lower()
            if user_input in ['guide', 'g']:
                webbrowser.open(guide_url)
                print("正在打开说明网页...")
                break
            elif user_input in ['help', 'h']:
                webbrowser.open(help_url)
                print("正在打开使用帮助...")
                break
            target_date, need_confirmation = parse_date_input(user_input)
        else:
            if not need_confirmation or input(f"即将自动获取{format_date_chinese(datetime.strptime(target_date, '%Y-%m/%d'))}所发行的《人民日报》（电子版），按回车确认。") == '':
                if datetime.strptime(target_date, '%Y-%m/%d') < datetime(2021, 1, 1):
                    print("本程序所有数据来自http://paper.people.com.cn/ ，此网站提供了2021年1月1日及以后发行的《人民日报》（电子版），更早的报纸暂未开放获取。")
                    continue

                articles_data, today = fetch_articles(target_date)
                if articles_data:
                    create_epub(articles_data, today)
                    print(f"已成功获取《人民日报》（电子版 {format_date_chinese(datetime.strptime(target_date, '%Y-%m/%d'))}）。您可以继续输入日期，或手动关闭窗口。")
                    continue
                else:
                    if datetime.now().hour < 6 and user_input == "":
                        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m/%d')
                        confirm_input = input(f"今天的《人民日报》（电子版）可能还没有发行，即将获取{format_date_chinese(datetime.strptime(yesterday, '%Y-%m/%d'))}的《人民日报》（电子版），按回车确认。")
                        if confirm_input in ['back', 'b']:
                            continue
                        articles_data, actual_date = fetch_articles(yesterday)
                        if articles_data:
                            create_epub(articles_data, actual_date)
                            print(f"《人民日报》{format_date_chinese(datetime.strptime(actual_date, '%Y-%m/%d'))}的电子版已经生成。")
                        else:
                            print("无法获取昨天的文章数据。")
                    continue