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
    try:
        res = requests.get("https://ygosu.com" + post_url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 댓글 목록 li들을 다 찾음
        replies = soup.find_all('li', class_='normal_reply')
        
        # 1. 댓글의 실제 작성 시간과 작성자를 추출
        comment_log = []
        for li in replies:
            # 닉네임과 아이디 추출
            a_tag = li.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag: continue
            
            # [핵심] 실제 작성 시간 파싱 (와이고수 댓글의 <div class='time'> 값)
            time_div = li.find('div', class_='time')
            raw_time = time_div.get_text(strip=True) if time_div else "00:00"
            
            onclick_text = a_tag.get('onclick', '')
            mem_id = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick_text)
            mem_id = mem_id.group(1) if mem_id else a_tag.get_text(strip=True)
            
            comment_log.append({"mem_id": mem_id, "name": a_tag.get_text(strip=True), "time": raw_time})
        
        return comment_log
    except:
        return []

def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 (20번째 댓글 기준 + DOM 인덱스 보정)")
    today_posters = set()
    user_names = {}
    post_urls = []
    comment_data = {}   # 유저별 (time, index) 리스트

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_board_page, range(1, 6))
        for page_posts in results:
            for p in page_posts:
                post_urls.append(p["url"])
                if p["is_today"]:
                    today_posters.add(p["mem_id"])
                    user_names[p["mem_id"]] = p["name"]

    print(f"  발견된 오늘 게시글: {len(today_posters)}개")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_comments_from_post, post_urls)
        for comments in results:
            for c in comments:
                m_id = c["mem_id"]
                user_names[m_id] = c["name"]
                comment_data.setdefault(m_id, []).append( (c["time"], c["comment_index"]) )

  final_achievers = []
    for m_id, logs in user_comment_logs.items():
        if len(logs) >= 20:
            # 20번째 댓글 작성 시간으로 정렬 (와이고수 시간 포맷에 맞춰 비교)
            logs.sort(key=lambda x: x['time']) 
            final_achievers.append({
                "mem_id": m_id,
                "name": logs[0]['name'],
                "time": logs[19]['time'] # 20번째 댓글 시간
            })
    
    # 시간 순으로 정렬하여 1등부터 순위 매기기
    final_achievers.sort(key=lambda x: x['time'])
    return final_achievers

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

    data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {mode} 모드 완료! data.json 업데이트 성공.")

if __name__ == "__main__":
    main()
