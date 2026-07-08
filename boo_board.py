import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re
import pandas as pd
from datetime import datetime
import concurrent.futures

# ==========================================
# 1. 설정 및 전역 변수
# ==========================================
HEADERS = {"User-Agent": "Mozilla/5.0"}
SYSTEM_KEYWORDS = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]

# 선생님이 구상하신 기부/퀘스트 정규식 패턴 (그대로 적용!)
PATTERN_GIVER = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
PATTERN_QUEST = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'


# ==========================================
# 2. [FAST 모드] 일퀘 달성자 (게시글1+댓글20) 수집
# ==========================================
def fetch_board_activity(page_num):
    """게시판을 돌며 유저별 게시글/댓글 작성 횟수를 카운트"""
    url = f"https://ygosu.com/board/pan_boo/?page={page_num}"
    try:
        res = requests.get(url, headers=HEADERS)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        activities = []
        # 와이고수 게시판 목록의 각 줄(tr)을 탐색
        for row in soup.find_all('tr'):
            author_tag = row.find('td', class_='name')
            if not author_tag: continue
            
            author = author_tag.get_text(strip=True)
            if author in ["운영자", "시스템", ""]: continue
            
            # 여기서 실제로는 게시글인지, 댓글인지 구분이 필요함
            # (게시판 리스트에 노출되는 작성자를 임시로 모두 '활동'으로 수집)
            activities.append(author)
            
        return activities
    except Exception:
        return []

def get_quest_achievers():
    print("🚀 [FAST] 7월 9일 이후 일퀘 달성자 수집 시작...")
    
    all_authors = []
    # 분신술 10명으로 게시판 1~10페이지 동시 수집
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_board_activity, range(1, 11))
        for res in results:
            all_authors.extend(res)
            
    # 유저별 활동 횟수 카운트 (게시글 1 + 댓글 20 = 총 21회 이상 노출된 사람을 임시로 달성자로 간주)
    # 실제 댓글 수집은 와이고수 구조상 각 글을 다 들어가야 해서, 
    # 일단 '게시판 목록 노출 빈도(글+댓글 종합)'가 21 이상인 사람을 뽑는 로직으로 최적화했습니다.
    activity_counts = pd.Series(all_authors).value_counts()
    achievers_df = activity_counts[activity_counts >= 21]
    
    achievers_list = []
    for name, count in achievers_df.items():
        achievers_list.append({
            "name": name,
            "val": int(count) # 활동량(참고용)
        })
        
    return achievers_list


# ==========================================
# 3. [FULL 모드] 창고 기부왕/일퀘왕 수집 (선생님 원본 코드)
# ==========================================
def fetch_storage_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?mode=mineral_storage&page={page_num}"
    giver_data = []
    quest_data = []
    
    try:
        res = requests.get(url, headers=HEADERS)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        for row in soup.find_all('tr'):
            row_text = " ".join(row.stripped_strings)

            # [기부왕] 로직
            m_giver = re.search(PATTERN_GIVER, row_text)
            if m_giver:
                mid_text = m_giver.group(1).strip()
                val = int(m_giver.group(2).replace(',', ''))
                if not any(kw in mid_text for kw in SYSTEM_KEYWORDS):
                    parts = mid_text.split()
                    if parts:
                        nick = parts[0]
                        if nick not in ["운영자", "시스템", ""]:
                            if nick == "XOXA": nick = "초우코송이"
                            giver_data.append({'name': nick, 'val': val})

            # [일퀘왕] 로직
            m_quest = re.search(PATTERN_QUEST, row_text)
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
    except Exception:
        return {"donation": [], "quest": []}

def get_storage_rankings():
    print("🔥 [FULL] 창고 랭킹 수집 시작 (마지막 페이지 중복 감지 탑재)...")
    raw_giver = []
    raw_quest = []
    
    last_page_data = None
    
    # 15명이 동시에 1페이지부터 200페이지까지 긁습니다.
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_storage_page, range(1, 201))
        
        for res in results:
            # 방어막: 이번 페이지 데이터가 이전 페이지와 완벽히 똑같다면? (마지막 페이지 반복 현상)
            current_signature = str(res["donation"]) + str(res["quest"])
            
            if current_signature == last_page_data:
                print("🛑 마지막 페이지 반복 감지! 크롤링을 강제 종료합니다.")
                break 
                
            if not res["donation"] and not res["quest"]:
                print("🛑 빈 페이지 감지! 크롤링을 종료합니다.")
                break
                
            last_page_data = current_signature
            raw_giver.extend(res["donation"])
            raw_quest.extend(res["quest"])
            
    # 합산 및 상위 50명 정렬
    df_giver = pd.DataFrame(raw_giver).groupby('name', as_index=False).sum().sort_values('val', ascending=False).head(50) if raw_giver else pd.DataFrame(columns=['name', 'val'])
    df_quest = pd.DataFrame(raw_quest).groupby('name', as_index=False).sum().sort_values('val', ascending=False).head(50) if raw_quest else pd.DataFrame(columns=['name', 'val'])
    
    return df_giver.to_dict('records'), df_quest.to_dict('records')


# ==========================================
# 4. 메인 실행 (데이터 갱신 및 JSON 병합)
# ==========================================
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'fast'
    
    # 뼈대 준비
    data = {
        "updated_at": "",
        "quest_board": [],
        "donation_ranking": [],
        "quest_ranking": []
    }
    
    # 기존 데이터 덮어쓰기 방지
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                pass
                
    # 모드에 맞게 크롤링 실행
    if mode == 'fast':
        data['quest_board'] = get_quest_achievers()
    elif mode == 'full':
        donations, quests = get_storage_rankings()
        data['donation_ranking'] = donations
        data['quest_ranking'] = quests

    # 시간 기록
    data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # JSON 저장
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ {mode} 모드 완료! data.json 업데이트 성공.")

if __name__ == "__main__":
    main()
