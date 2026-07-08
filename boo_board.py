import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re
import pandas as pd
from datetime import datetime
import concurrent.futures
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ---------- FAST 모드 (게시글/댓글) ----------
def process_board_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?page={page_num}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = []
        for tr in soup.select('table.bd_list tr'):
            date_td = tr.find('td', class_='date')
            if not date_td:
                continue
            date_text = date_td.get_text(strip=True)
            is_today = (':' in date_text) or ('전' in date_text) or ('방금' in date_text)

            name_td = tr.find('td', class_='name')
            if not name_td:
                continue
            a_tag = name_td.find('a', onclick=True)
            if not a_tag:
                continue
            onclick = a_tag.get('onclick', '')
            match = re.search(r"show_nick_dropdown\([^,]+,\s*'[^']*',\s*'([^']+)'", onclick)
            mem_id = match.group(1) if match else None
            name = a_tag.get_text(strip=True)
            if not mem_id:
                continue

            tit_td = tr.find('td', class_='tit')
            if not tit_td:
                continue
            link_tag = tit_td.find('a')
            if not link_tag or not link_tag.get('href'):
                continue

            posts.append({
                "url": link_tag['href'],
                "is_today": is_today,
                "mem_id": mem_id,
                "name": name
            })
        return posts
    except Exception as e:
        return []

def get_comments_from_post(post_url):
    if not post_url.startswith('http'):
        post_url = "https://ygosu.com" + post_url
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        today_comments = []
        for li in soup.find_all('li', class_='normal_reply'):
            time_div = li.find('div', class_='time')
            if not time_div:
                continue
            time_text = time_div.get_text(strip=True)
            if not any(kw in time_text for kw in ['전', '방금', ':']):
                continue

            comment_time = parse_relative_time(time_text)

            a_tag = li.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag:
                continue
            onclick = a_tag.get('onclick', '')
            match = re.search(r"show_nick_dropdown\([^,]+,\s*'[^']*',\s*'([^']+)'", onclick)
            if match:
                mem_id = match.group(1)
                name = a_tag.get_text(strip=True)
                today_comments.append({
                    "mem_id": mem_id,
                    "name": name,
                    "time": comment_time
                })
        return today_comments
    except:
        return []

from datetime import datetime, timedelta

def parse_relative_time(text):
    now = datetime.now()
    text = text.strip()
    if '방금' in text or '초 전' in text:
        return now
    if '분 전' in text:
        m = re.search(r'(\d+)분 전', text)
        if m:
            return now - timedelta(minutes=int(m.group(1)))
    if '시간 전' in text:
        m = re.search(r'(\d+)시간 전', text)
        if m:
            return now - timedelta(hours=int(m.group(1)))
    if ':' in text:
        parts = text.split(':')
        if len(parts) == 2:
            h, m = int(parts[0]), int(parts[1])
            return now.replace(hour=h, minute=m, second=0, microsecond=0)
    return now
    
def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 (게시글 1 + 댓글 20)")
    today_posters = set()
    user_names = {}
    post_urls = []
    comment_counts = {}
    earliest_comment = {}   # 각 유저의 가장 이른 댓글 시간

    # 게시글 수집 (기존과 동일)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_board_page, range(1, 6))
        for page_posts in results:
            for p in page_posts:
                post_urls.append(p["url"])
                if p["is_today"]:
                    today_posters.add(p["mem_id"])
                    user_names[p["mem_id"]] = p["name"]

    # 댓글 수집
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_comments_from_post, post_urls)
        for comments in results:
            for c in comments:
                m_id = c["mem_id"]
                user_names[m_id] = c["name"]
                comment_counts[m_id] = comment_counts.get(m_id, 0) + 1
                # 가장 이른 시간 기록
                if m_id not in earliest_comment or c["time"] < earliest_comment[m_id]:
                    earliest_comment[m_id] = c["time"]

    # 조건 만족자 추출
    achievers = []
    for m_id, c_count in comment_counts.items():
        if m_id in today_posters and c_count >= 20:
            achievers.append({
                "mem_id": m_id,
                "name": user_names[m_id],
                "earliest_time": earliest_comment.get(m_id, datetime.max)
            })

    # 이른 시간 순으로 정렬 (가장 먼저 달성한 사람이 1등)
    achievers.sort(key=lambda x: x["earliest_time"])
    # 결과에서 'earliest_time'은 제거하고 val="달성" 추가
    result = []
for a in achievers:
    result.append({"mem_id": a["mem_id"], "name": a["name"], "val": "CLEAR"})
return result
# ---------- FULL 모드 (미네랄 창고) ----------
def fetch_storage_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?mode=mineral_storage&page={page_num}"
    pattern_giver = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
    pattern_quest = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'
    system_keywords = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]

    for attempt in range(3):
        try:
            time.sleep(random.uniform(0.3, 0.8))
            res = requests.get(url, headers=HEADERS, timeout=15)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')

            giver_data = []
            quest_data = []
            for row in soup.find_all('tr'):
                row_text = " ".join(row.stripped_strings)

               # 기부
m_giver = re.search(pattern_giver, row_text)
if m_giver:
    mid_text = m_giver.group(1).strip()
    val = int(m_giver.group(2).replace(',', ''))
    if not any(kw in mid_text for kw in system_keywords):
        parts = mid_text.split()
        if parts:
            nick = parts[0]
            if nick not in ["운영자", "시스템", ""]:
                if nick == "XOXA":
                    nick = "초우코송이"
                # 10억 이상이면 무시
                if val <= 1000000000:
                    giver_data.append({'name': nick, 'val': val})
                    
                # 일퀘 (수정)
m_quest = re.search(pattern_quest, row_text)
if m_quest:
    mid_text = m_quest.group(1).strip()
    val = int(m_quest.group(2).replace(',', ''))
    # 시스템 메시지 제외
    if not any(kw in mid_text for kw in system_keywords) and "에게" in mid_text:
        parts = mid_text.split('에게')[0].split()
        if parts:
            nick = parts[-1]
            if nick not in ["운영자", "시스템", ""]:
                quest_data.append({'name': nick, 'val': val})
            return {"donation": giver_data, "quest": quest_data}
        except Exception as e:
            print(f"  ⚠️ 페이지 {page_num} 재시도 {attempt+1}/3 - {e}")
            time.sleep(2)
    return {"donation": [], "quest": []}

def get_storage_rankings():
    print("🔥 [FULL] 미네랄 창고 크롤링 시작 (코랩 검증 정규식 사용)")
    # 창고는 보통 110~120페이지 사이, 안전하게 120까지 시도
    total_pages = 120
    raw_giver = []
    raw_quest = []

    for page in range(1, total_pages + 1):
        print(f"⏳ 페이지 {page}/{total_pages} 처리 중...", end=" ")
        result = fetch_storage_page(page)
        g_count = len(result["donation"])
        q_count = len(result["quest"])
        print(f"기부 {g_count}건, 지급 {q_count}건")
        raw_giver.extend(result["donation"])
        raw_quest.extend(result["quest"])

    print(f"\n✅ 전체 수집 완료: 기부 {len(raw_giver)}건, 지급 {len(raw_quest)}건")

    df_giver = pd.DataFrame(raw_giver)
    df_quest = pd.DataFrame(raw_quest)

    if not df_giver.empty:
        df_giver = df_giver.groupby('name', as_index=False)['val'].sum().sort_values('val', ascending=False).head(50)
        donation_ranking = df_giver.to_dict('records')
    else:
        donation_ranking = []

    if not df_quest.empty:
        df_quest = df_quest.groupby('name', as_index=False)['val'].sum().sort_values('val', ascending=False).head(50)
        quest_ranking = df_quest.to_dict('records')
    else:
        quest_ranking = []

    return donation_ranking, quest_ranking

# 메인 실행부
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'fast'
    data = {
        "updated_at": "",
        "quest_board": [],
        "donation_ranking": [],
        "quest_ranking": []
    }

    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except: pass

    if mode == 'fast':
        data['quest_board'] = get_quest_achievers()
    elif mode == 'full':
        donations, quests = get_storage_rankings()
        data['donation_ranking'] = donations
        data['quest_ranking'] = quests

    data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {mode} 모드 완료! data.json 업데이트 성공.")

if __name__ == "__main__":
    main()
