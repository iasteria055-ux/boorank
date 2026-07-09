import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ========== FAST 모드 (게시글 + 댓글 → 일퀘 달성자) ==========
def process_board_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?page={page_num}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = []
        for tr in soup.find_all('tr'):
            date_td = tr.find('td', class_='date')
            if not date_td:
                continue
            date_text = date_td.get_text(strip=True)

            # ★ 오늘 게시글은 HH:MM 형식만
            is_today = bool(re.match(r'^\d{2}:\d{2}$', date_text))
            post_time = None
            if is_today:
                try:
                    h, mi = map(int, date_text.split(':'))
                    now = datetime.now()
                    # 오늘 날짜에 해당 시간을 그대로 적용 (미래여도 보정하지 않음)
                    post_time = now.replace(hour=h, minute=mi, second=0, microsecond=0)
                    # 단, 23:59 vs 00:01 같은 극단적 케이스는 없으므로 무시
                except:
                    post_time = None

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
                "name": name,
                "post_time": post_time   # 오늘인 경우만 값 존재
            })
        return posts
    except Exception as e:
        print(f"  [process_board_page] 페이지 {page_num} 오류: {e}")
        return []

def parse_relative_time(text):
    """'4시간 전', '방금', '00:51' 등 오늘 시간을 datetime으로 변환
       'X일 전'은 오늘이 아니므로 None 반환 → 집계 제외"""
    now = datetime.now()
    text = text.strip()
    if '방금' in text or '초 전' in text:
        return now
    if '분 전' in text:
        m = re.search(r'(\d+)\s*분\s*전', text)
        if m:
            return now - timedelta(minutes=int(m.group(1)))
    if '시간 전' in text:
        m = re.search(r'(\d+)\s*시간\s*전', text)
        if m:
            return now - timedelta(hours=int(m.group(1)))
    if re.match(r'^\s*\d{1,2}:\d{2}\s*$', text):
        h, mi = map(int, text.strip().split(':'))
        return now.replace(hour=h, minute=mi, second=0, microsecond=0)
    # 'X일 전', '어제' 등은 오늘이 아니므로 None
    return None

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
                    "name": name
                })
        return today_comments
    except Exception as e:
        print(f"  [get_comments] 오류: {e} (게시글: {post_url})")
        return []

def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 (게시글 작성 순 기준)")
    today_posters = set()
    user_names = {}
    post_times = {}   # 게시글 URL -> 작성 시간
    comment_counts = {}
    user_earliest_post = {}   # 유저가 댓글을 단 게시글 중 가장 이른 시간

    # 1. 게시글 수집 (post_time 포함)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_board_page, range(1, 6))
        for page_posts in results:
            for p in page_posts:
                if p["is_today"]:
                    today_posters.add(p["mem_id"])
                    user_names[p["mem_id"]] = p["name"]
                if p["post_time"]:
                    post_times[p["url"]] = p["post_time"]

    print(f"  발견된 오늘 게시글: {len(today_posters)}개")

    # 2. 댓글 수집 및 각 유저의 가장 이른 게시글 시간 기록
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 게시글 URL 리스트를 만들고, 각 URL과 댓글 결과를 매칭
        post_urls = list(post_times.keys())
        results = executor.map(get_comments_from_post, post_urls)
        for post_url, comments in zip(post_urls, results):
            post_time = post_times[post_url]
            for c in comments:
                m_id = c["mem_id"]
                user_names[m_id] = c["name"]
                comment_counts[m_id] = comment_counts.get(m_id, 0) + 1
                # 이 유저가 이 게시글에 댓글을 달았으므로, 가장 이른 게시글 시간 업데이트
                if m_id not in user_earliest_post or post_time < user_earliest_post[m_id]:
                    user_earliest_post[m_id] = post_time

    # 3. 조건 충족자 추출
    achievers = []
    for m_id, c_count in comment_counts.items():
        if m_id in today_posters and c_count >= 20:
            earliest_time = user_earliest_post.get(m_id, datetime.max)
            achievers.append({
                "mem_id": m_id,
                "name": user_names[m_id],
                "earliest": earliest_time
            })
            print(f"  {user_names[m_id]}: 가장 이른 게시글 시간 = {earliest_time}")

    if not achievers:
        print("  ❌ 조건을 만족한 사람이 없습니다.")

    # 4. 정렬: 게시글 작성 시간이 빠른 순서 (먼저 작성된 게시글에서 활동한 사람이 1등)
    achievers.sort(key=lambda x: x["earliest"])
    return [{"mem_id": a["mem_id"], "name": a["name"], "val": "CLEAR"} for a in achievers]
# ========== FULL 모드 (미네랄 창고 → 기부왕, 일퀘왕) ==========
def fetch_storage_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?mode=mineral_storage&page={page_num}"
    pattern_giver = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
    pattern_quest = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'
    system_keywords = [
        "게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템",
        "수수료", "당첨", "보상", "지급", "미네랄 출금"
    ]

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
                                giver_data.append({'name': nick, 'val': val})

                m_quest = re.search(pattern_quest, row_text)
                if m_quest:
                    mid_text = m_quest.group(1).strip()
                    val = int(m_quest.group(2).replace(',', ''))
                    if "에게" in mid_text:
                        if not any(kw in mid_text for kw in system_keywords):
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
    print("🔥 [FULL] 미네랄 창고 크롤링 시작 (중복 페이지 자동 종료)")
    raw_giver = []
    raw_quest = []
    prev_sig = None

    for page in range(1, 200):
        result = fetch_storage_page(page)
        g_count = len(result['donation'])
        q_count = len(result['quest'])
        print(f"⏳ 페이지 {page} 처리 중... 기부 {g_count}건, 지급 {q_count}건")

        curr_sig = str(result['donation']) + str(result['quest'])
        if curr_sig == prev_sig:
            print(f"🛑 {page-1}페이지가 마지막입니다. 크롤링 종료.")
            break
        prev_sig = curr_sig

        raw_giver.extend(result["donation"])
        raw_quest.extend(result["quest"])

    print(f"✅ 수집 완료: 기부 {len(raw_giver)}건, 지급 {len(raw_quest)}건")

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

# ========== 메인 ==========
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
            try:
                data = json.load(f)
            except:
                pass

    if mode == 'fast':
        data['quest_board'] = get_quest_achievers()
    elif mode == 'full':
        donations, quests = get_storage_rankings()
        data['donation_ranking'] = donations
        data['quest_ranking'] = quests

# 1. 일퀘 달성자들을 시간 순으로 정렬 (데이터 들어온 순서 상관없음)
    data['quest_board'] = sorted(
        data['quest_board'], 
        key=lambda x: x.get('time', '23:59:59')
    )

    # 기부왕/일퀘왕도 혹시 모를 val 키 누락 방지
    data['donation_ranking'] = sorted(data['donation_ranking'], key=lambda x: x.get('val', 0), reverse=True)
    data['quest_ranking'] = sorted(data['quest_ranking'], key=lambda x: x.get('val', 0), reverse=True)

    data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {mode} 모드 완료! data.json 업데이트 성공.")

if __name__ == "__main__":
    main()
