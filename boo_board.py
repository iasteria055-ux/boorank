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
    """ '방금', 'X분 전', 'X시간 전', 'HH:MM' → datetime """
    now = datetime.now()
    text = text.strip()
    if '방금' in text or '초 전' in text:
        return now
    m = re.search(r'(\d+)\s*분\s*전', text)
    if m:
        return now - timedelta(minutes=int(m.group(1)))
    m = re.search(r'(\d+)\s*시간\s*전', text)
    if m:
        return now - timedelta(hours=int(m.group(1)))
    if re.match(r'^\s*\d{1,2}:\d{2}\s*$', text):
        h, mi = map(int, text.strip().split(':'))
        return now.replace(hour=h, minute=mi, second=0, microsecond=0)
    # 파싱 실패 → None
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
            comment_time = parse_relative_time(time_text)
            if comment_time is None:
                print(f"    ⚠️ 시간 파싱 실패: '{time_text}' (게시글: {post_url})")
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
                    "name": name,
                    "time": comment_time
                })
        return today_comments
    except Exception as e:
        print(f"  [get_comments] 오류: {e} (게시글: {post_url})")
        return []

def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 (게시글 1 + 댓글 20)")
    today_posters = set()
    user_names = {}
    post_urls = []
    comment_times = {}      # 유저별 댓글 시간 리스트

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
                comment_times.setdefault(m_id, []).append(c["time"])

    achievers = []
    for m_id, times in comment_times.items():
        if m_id in today_posters and len(times) >= 20:
            times.sort()
            completion_time = times[19]   # 20번째 댓글
            achievers.append({
                "mem_id": m_id,
                "name": user_names[m_id],
                "completed_at": completion_time
            })
            print(f"  {user_names[m_id]}: 20번째 댓글 시간 = {completion_time}")

    if not achievers:
        print("  ❌ 조건을 만족한 사람이 없습니다.")

    # 완료 시간 오름차순 → 가장 먼저 20개를 채운 사람이 1등
    achievers.sort(key=lambda x: x["completed_at"])
    return [{"mem_id": a["mem_id"], "name": a["name"], "val": "CLEAR"} for a in achievers]

# ========== FULL 모드 (기존과 동일) ==========
# ... (생략 - 이전에 제공한 정규식 기반 fetch_storage_page 사용)

def main():
    # ... (동일)
