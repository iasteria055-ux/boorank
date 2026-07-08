import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re
import pandas as pd
from datetime import datetime
import concurrent.futures

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ==========================================
# 1. [FAST 모드] 일퀘 달성자 (오늘 게시글 1 + 댓글 20)
# ==========================================
def process_board_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?page={page_num}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = []
        for tr in soup.find_all('tr'):
            date_td = tr.find('td', class_='date')
            if not date_td: continue
            date_text = date_td.get_text(strip=True)

            # 와이고수 특성: 오늘 작성된 글은 "00:51" 처럼 콜론(:)이 포함됨
            is_today = ":" in date_text

            a_tag = tr.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag: continue

            mem_id = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", a_tag.get('onclick', ''))
            mem_id = mem_id.group(1) if mem_id else a_tag.get_text(strip=True)
            name = a_tag.get_text(strip=True)

            link_tag = tr.find('td', class_='tit').find('a') if tr.find('td', class_='tit') else None
            if link_tag and link_tag.get('href'):
                posts.append({"url": link_tag['href'], "is_today": is_today, "mem_id": mem_id, "name": name})
        return posts
    except:
        return []

def get_comments_from_post(post_url):
    if not post_url.startswith('http'):
        post_url = "https://ygosu.com" + post_url
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        today_comments = []
        for li in soup.find_all('li', class_='normal_reply'):
            time_div = li.find('div', class_='time')
            if not time_div: continue
            time_text = time_div.get_text(strip=True)

            # 댓글 시간이 "전", "방금", 혹은 ":" 이 포함되면 오늘 쓴 댓글로 인정
            if any(kw in time_text for kw in ["전", "방금", ":"]):
                a_tag = li.find('a', onclick=re.compile(r'show_nick_dropdown'))
                if a_tag:
                    mem_id = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", a_tag.get('onclick', ''))
                    mem_id = mem_id.group(1) if mem_id else a_tag.get_text(strip=True)
                    name = a_tag.get_text(strip=True)
                    today_comments.append({"mem_id": mem_id, "name": name})
        return today_comments
    except:
        return []

def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 (오늘자 게시글 1 + 댓글 20 실시간 검증)...")
    today_posters = set()
    user_names = {}
    post_urls = []
    comment_counts = {}

    # 1. 최신 1~5페이지에서 오늘 쓴 게시글 및 작성자 수집
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_board_page, range(1, 6))
        for page_posts in results:
            for p in page_posts:
                post_urls.append(p["url"])
                if p["is_today"]:
                    today_posters.add(p["mem_id"])
                    user_names[p["mem_id"]] = p["name"]

    # 2. 수집된 게시글 본문에 들어가서 '오늘' 달린 댓글 싹 다 카운트 (스레드 15개로 초고속 렌더링)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(get_comments_from_post, post_urls)
        for comments in results:
            for c in comments:
                m_id = c["mem_id"]
                user_names[m_id] = c["name"]
                comment_counts[m_id] = comment_counts.get(m_id, 0) + 1

    # 3. 조건 필터링 (오늘 게시글 1회 이상 AND 댓글 20회 이상)
    achievers = []
    for m_id, c_count in comment_counts.items():
        if m_id in today_posters and c_count >= 20:
            achievers.append({
                "mem_id": m_id,
                "name": user_names[m_id],
                "val": "달성"
            })

    return achievers

# ==========================================
# 2. [FULL 모드] 창고 랭킹 수집 (메모 버그 픽스 + 300페이지 딥서치)
# ==========================================
def fetch_storage_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?mode=mineral_storage&page={page_num}"
    giver_data = []
    quest_data = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for row in soup.find_all('tr'):
            # a태그(닉네임 클릭)가 없으면 100% 시스템 메시지이므로 차단
            a_tag = row.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag: continue

            onclick_text = a_tag.get('onclick', '')
            id_match = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick_text)
            mem_id = id_match.group(1) if id_match else None
            nick = a_tag.get_text(strip=True)

            if not mem_id or nick in ["운영자", "시스템", ""]:
                continue
            if nick == "XOXA": nick = "초우코송이"

            row_text = " ".join(row.stripped_strings)

            # 핵심: 게시판 창고 기준 '+'는 무조건 유저 기부, '-'는 무조건 일퀘 지급
            # 메모(글자) 필터링을 아예 없애서 이벤트/메모 기부액 누락 방지
            m_plus = re.search(r'\+\s*([0-9,]+)', row_text)
            m_minus = re.search(r'-\s*([0-9,]+)', row_text)

            if m_plus:
                val = int(m_plus.group(1).replace(',', ''))
                giver_data.append({'name': nick, 'mem_id': mem_id, 'val': val})
            elif m_minus:
                val = int(m_minus.group(1).replace(',', ''))
                quest_data.append({'name': nick, 'mem_id': mem_id, 'val': val})

        return {"donation": giver_data, "quest": quest_data}
    except:
        return {"donation": [], "quest": []}

def get_storage_rankings():
    print("🔥 [FULL] 창고 랭킹 수집 (누락 없는 300페이지 딥서치)...")
    raw_giver = []
    raw_quest = []
    seen_signatures = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_storage_page, range(1, 301))
        for res in results:
            sig = str(res["donation"]) + str(res["quest"])
            if (not res["donation"] and not res["quest"]) or sig in seen_signatures:
                break # 와이고수 마지막 페이지 반복 시 즉시 종료
            seen_signatures.add(sig)
            raw_giver.extend(res["donation"])
            raw_quest.extend(res["quest"])

    # 닉네임을 변경했더라도 mem_id 기준으로 합산되도록 스마트 그룹화 적용
    df_giver = pd.DataFrame(raw_giver).groupby('mem_id', as_index=False).agg({'name': 'first', 'val': 'sum'}).sort_values('val', ascending=False).head(50) if raw_giver else pd.DataFrame(columns=['mem_id', 'name', 'val'])
    df_quest = pd.DataFrame(raw_quest).groupby('mem_id', as_index=False).agg({'name': 'first', 'val': 'sum'}).sort_values('val', ascending=False).head(50) if raw_quest else pd.DataFrame(columns=['mem_id', 'name', 'val'])

    return df_giver.to_dict('records'), df_quest.to_dict('records')

# ==========================================
# 3. 메인 실행부
# ==========================================
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'fast'
    data = {"updated_at": "", "quest_board": [], "donation_ranking": [], "quest_ranking": []}

    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except json.JSONDecodeError: pass

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
