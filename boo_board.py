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
# 1. 설정 및 글로벌 변수
# ==========================================
HEADERS = {"User-Agent": "Mozilla/5.0"}
SYSTEM_KEYWORDS = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]
PATTERN_GIVER = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
PATTERN_QUEST = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'

# ==========================================
# 2. [FAST 모드] 일퀘 달성자 수집
# ==========================================
def fetch_board_activity(page_num):
    url = f"https://ygosu.com/board/pan_boo/?page={page_num}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        activities = []
        for row in soup.find_all('tr'):
            a_tag = row.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag: continue
            
            nick = a_tag.get_text(strip=True)
            if nick in ["운영자", "시스템", ""]: continue
            
            onclick_text = a_tag.get('onclick', '')
            id_match = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick_text)
            mem_id = id_match.group(1) if id_match else nick
            
            activities.append({"name": nick, "mem_id": mem_id})
            
        return activities
    except Exception as e:
        print(f"Board Page {page_num} Error: {e}")
        return []

def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 시작...")
    all_authors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_board_activity, range(1, 11))
        for res in results:
            all_authors.extend(res)
            
    df = pd.DataFrame(all_authors)
    if df.empty: return []
    
    counts = df.groupby(['mem_id', 'name']).size().reset_index(name='val')
    achievers_df = counts[counts['val'] >= 1].sort_values('val', ascending=False)
    
    return achievers_df.to_dict('records')

# ==========================================
# 3. [FULL 모드] 창고 랭킹 수집 (불도저 모드)
# ==========================================
def fetch_storage_page(page_num):
    url = f"https://ygosu.com/board/pan_boo/?mode=mineral_storage&page={page_num}"
    giver_data = []
    quest_data = []
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200: return {"donation": [], "quest": []}
        
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        for row in soup.find_all('tr'):
            mem_id = None
            a_tag = row.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if a_tag:
                onclick_text = a_tag.get('onclick', '')
                id_match = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick_text)
                if id_match: mem_id = id_match.group(1)

            row_text = " ".join(row.stripped_strings)

            # 기부왕 파싱
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
                            final_id = mem_id if mem_id else nick 
                            giver_data.append({'name': nick, 'mem_id': final_id, 'val': val})

            # 일퀘왕 파싱
            m_quest = re.search(PATTERN_QUEST, row_text)
            if m_quest:
                mid_text = m_quest.group(1).strip()
                val = int(m_quest.group(2).replace(',', ''))
                if "에게" in mid_text:
                    parts = mid_text.split('에게')[0].split()
                    if parts:
                        nick = parts[-1]
                        if nick not in ["운영자", "시스템", ""]:
                            final_id = mem_id if mem_id else nick
                            quest_data.append({'name': nick, 'mem_id': final_id, 'val': val})
                            
        return {"donation": giver_data, "quest": quest_data}
    except Exception as e:
        print(f"Storage Page {page_num} Error: {e}")
        return {"donation": [], "quest": []}

def get_storage_rankings():
    print("🔥 [FULL] 창고 랭킹 수집 (완벽 중복 차단 필터 적용)...")
    raw_giver = []
    raw_quest = []
    
    seen_signatures = set() # 중복 페이지를 감지하는 블랙리스트
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_storage_page, range(1, 151))
        
        for res in results:
            if not res["donation"] and not res["quest"]:
                continue # 빈 페이지는 일단 무시하고 진행
                
            # 현재 페이지의 데이터를 문자열로 압축해서 고유 지문 생성
            page_signature = str(res["donation"]) + str(res["quest"])
            
            # 만약 이 지문이 블랙리스트에 있다면? (와이고수가 마지막 페이지를 반복해서 보여주는 상황)
            if page_signature in seen_signatures:
                print("🛑 중복 페이지(끝 페이지) 감지! 크롤링을 종료합니다.")
                break 
                
            seen_signatures.add(page_signature)
            raw_giver.extend(res["donation"])
            raw_quest.extend(res["quest"])
            
    df_giver = pd.DataFrame(raw_giver).groupby(['mem_id', 'name'], as_index=False).sum().sort_values('val', ascending=False).head(50) if raw_giver else pd.DataFrame(columns=['mem_id', 'name', 'val'])
    df_quest = pd.DataFrame(raw_quest).groupby(['mem_id', 'name'], as_index=False).sum().sort_values('val', ascending=False).head(50) if raw_quest else pd.DataFrame(columns=['mem_id', 'name', 'val'])
    
    return df_giver.to_dict('records'), df_quest.to_dict('records')

# ==========================================
# 4. 메인 실행부
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
