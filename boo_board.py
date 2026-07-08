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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 1. [FAST 모드] 일퀘 달성자 (오늘 게시글 1 + 댓글 20)
# ==========================================

def process_board_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?page={page_num}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = []

        # 게시글 테이블이 어떤 구조인지에 따라 적절히 탐색
        # 보통은 div.board_list > table > tbody > tr
        for tr in soup.select('div.board_list tr, table.board_list tr, tr:has(td.tit)'):
            # 날짜 찾기: 모든 td 중에서 시간 패턴 (HH:MM, 전, 방금, MM-DD) 포함된 텍스트
            date_td = tr.find('td', string=re.compile(r'(\d{2}:\d{2}|전|방금|\d{2}-\d{2})'))
            if not date_td:
                continue
            date_text = date_td.get_text(strip=True)

            # 오늘 날짜인지 판단: ':' 또는 '전' 또는 '방금'이 있으면 오늘
            is_today = (':' in date_text) or ('전' in date_text) or ('방금' in date_text)

            # 닉네임 a 태그 찾기 (onclick이 없을 수도 있으니 href도 고려)
            a_tag = tr.find('a', href=re.compile(r'(minilog|pan_boo.*member)'))
            if not a_tag:
                # onclick으로 찾기
                a_tag = tr.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag:
                # 그냥 text가 있는 a 태그 (부정확할 수 있음)
                a_tag = tr.find('a', href=True)
                if a_tag and not a_tag.get_text(strip=True):
                    a_tag = None
            if not a_tag:
                continue

            name = a_tag.get_text(strip=True)
            mem_id = None

            # mem_id 추출 시도 1: onclick
            onclick = a_tag.get('onclick', '')
            match = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick)
            if match:
                mem_id = match.group(1)
            else:
                # 추출 시도 2: href에서 member 파라미터
                href = a_tag.get('href', '')
                m = re.search(r'member=([^&"\' ]+)', href)
                if m:
                    mem_id = m.group(1)
                else:
                    # fallback: 닉네임을 mem_id로 사용 (중복 가능성)
                    mem_id = name

            # 게시글 링크 찾기
            link_tag = tr.select_one('td.tit a, a.post_link, a[href*="board/read"]')
            if not link_tag:
                # 아무 링크나
                link_tag = a_tag  # 대체로 닉네임 a와 게시글 a가 다름. 더 정밀한 탐색 필요
            post_url = link_tag.get('href', '') if link_tag else ''

            if post_url:
                posts.append({
                    "url": post_url,
                    "is_today": is_today,
                    "mem_id": mem_id,
                    "name": name
                })
        return posts
    except Exception as e:
        print(f"페이지 {page_num} 파싱 오류: {e}")
        return []

def get_comments_from_post(post_url):
    if not post_url.startswith('http'):
        post_url = "https://ygosu.com" + post_url
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        today_comments = []

        # 댓글 리스트: li.comment, li.reply, li.normal_reply 등 가능
        comment_items = soup.select('li.comment, li.reply, li.normal_reply, div.comment_item')
        for item in comment_items:
            # 시간 표시 요소: div.time, span.time, span.date
            time_el = item.select_one('div.time, span.time, span.date')
            if not time_el:
                continue
            time_text = time_el.get_text(strip=True)

            # 오늘 댓글 여부 판단
            if not any(kw in time_text for kw in ['전', '방금', ':']):
                continue

            # 닉네임과 mem_id 추출 (게시글과 동일한 방식)
            a_tag = item.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag:
                a_tag = item.find('a', href=re.compile(r'minilog|member'))
            if not a_tag:
                continue

            name = a_tag.get_text(strip=True)
            mem_id = None
            onclick = a_tag.get('onclick', '')
            match = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick)
            if match:
                mem_id = match.group(1)
            else:
                href = a_tag.get('href', '')
                m = re.search(r'member=([^&"\' ]+)', href)
                if m:
                    mem_id = m.group(1)
                else:
                    mem_id = name

            today_comments.append({"mem_id": mem_id, "name": name})
        return today_comments
    except Exception as e:
        # print(f"댓글 수집 오류: {e}")  # 필요시 로그
        return []

def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 (오늘 게시글 1 + 댓글 20)...")
    today_posters = set()
    user_names = {}
    post_urls = []
    comment_counts = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_board_page, range(1, 6))
        for page_posts in results:
            for p in page_posts:
                post_urls.append(p["url"])
                if p["is_today"]:
                    today_posters.add(p["mem_id"])
                    user_names[p["mem_id"]] = p["name"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(get_comments_from_post, post_urls)
        for comments in results:
            for c in comments:
                m_id = c["mem_id"]
                user_names[m_id] = c["name"]
                comment_counts[m_id] = comment_counts.get(m_id, 0) + 1

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
# 2. [FULL 모드] 미네랄 창고 크롤링 (수수료 제외 + 자동 마지막 페이지)
# ==========================================
def is_system_row(row):
    """수수료, 운영자 메시지 등 시스템 로우인지 판별"""
    a_tag = row.find('a', href=True)
    if not a_tag:
        return True
    nick = a_tag.get_text(strip=True)
    if nick in ["운영자", "시스템", ""]:
        return True
    row_text = " ".join(row.stripped_strings)
    if any(kw in row_text for kw in ["미네랄 출금 수수료", "출금 수수료", "수수료", "이벤트", "공지"]):
        return True
    return False

import time
import random

def fetch_storage_page(page_num, retries=3):
    url = f"https://ygosu.com/board/pan_boo/?mode=mineral_storage&page={page_num}"
    pattern_giver = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
    pattern_quest = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'
    system_keywords = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]

    for attempt in range(retries):
        try:
            # 0.5~1.5초 랜덤 지연 (서버 부하 분산)
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
                                if nick == "XOXA": nick = "초우코송이"
                                giver_data.append({'name': nick, 'val': val})

                # 일퀘
                m_quest = re.search(pattern_quest, row_text)
                if m_quest:
                    mid_text = m_quest.group(1).strip()
                    val = int(m_quest.group(2).replace(',', ''))
                    if "에게" in mid_text:
                        parts = mid_text.split('에게')[0].split()
                        if parts:
                            nick = parts[-1]
                            if nick not in ["운영자", "시스템", ""]:
                                quest_data.append({'name': nick, 'val': val})
            return {"donation": giver_data, "quest": quest_data}
        except Exception as e:
            print(f"  ⚠️ 페이지 {page_num} 재시도 {attempt+1}/{retries} - 오류: {e}")
            time.sleep(2)  # 실패 시 좀 더 기다림
    print(f"  ❌ 페이지 {page_num} 최종 실패, 빈 리스트 반환")
    return {"donation": [], "quest": []}

def get_total_pages():
    """창고 게시판의 마지막 페이지 번호를 가져온다."""
    url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        last_page = 1
        # 하단 페이지네이션에서 마지막 페이지 링크 찾기
        # 보통 <a href="...page=111">111</a> 형태
        for a in soup.select('div.paging a, .pagination a, a.page_num'):
            href = a.get('href', '')
            if 'page=' in href:
                match = re.search(r'page=(\d+)', href)
                if match:
                    page_num = int(match.group(1))
                    if page_num > last_page:
                        last_page = page_num
        return last_page
    except:
        return 120  # 실패 시 기본값 (현재 111이므로 넉넉하게)

def get_storage_rankings():
    print("🔥 [FULL] 미네랄 창고 크롤링 시작 (순차 모드, 누락 방지)...")
    total_pages = get_total_pages()
    print(f"📊 총 {total_pages}페이지를 순차적으로 수집합니다.\n")

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

    print(f"\n✅ 전체 수집 완료: 기부 {len(raw_giver)}건, 지급 {len(raw_quest)}건\n")

    # 집계
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

# ==========================================
# 3. 메인 실행부
# ==========================================
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
            except json.JSONDecodeError:
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
