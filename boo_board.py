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
    url = f"https://ygosu.com/board/pan_boo/?page={page_num}"
    try:
        res = requests.get(url, headers=HEADERS)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        activities = []
        for row in soup.find_all('tr'):
            a_tag = row.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag: continue
            
            nick = a_tag.get_text(strip=True)
            if nick in ["운영자", "시스템", ""]: continue
            
            # 여기서 고유 아이디(mem_id)를 추출!
            onclick_text = a_tag.get('onclick', '')
            id_match = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick_text)
            mem_id = id_match.group(1) if id_match else nick
            
            activities.append({"name": nick, "mem_id": mem_id})
            
        return activities
    except Exception:
        return []

def get_quest_achievers():
    print("🚀 [FAST] 일퀘 달성자 수집 (고유 아이디 추출)...")
    all_authors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_board_activity, range(1, 11))
        for res in results:
            all_authors.extend(res)
            
    df = pd.DataFrame(all_authors)
    if df.empty: return []
    
    # 닉네임과 아이디를 묶어서 카운트
    counts = df.groupby(['mem_id', 'name']).size().reset_index(name='val')
    # TODO: 원래 '21'이었으나 데이터 노출 테스트를 위해 '1'로 임시 하향
    achievers_df = counts[counts['val'] >= 1].sort_values('val', ascending=False) 
    
    return achievers_df.to_dict('records')


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
            # 1. 닉네임과 고유 아이디 추출
            a_tag = row.find('a', onclick=re.compile(r'show_nick_dropdown'))
            if not a_tag: continue
            
            nick = a_tag.get_text(strip=True)
            if nick in ["운영자", "시스템", ""]: continue
            if nick == "XOXA": nick = "초우코송이"
            
            onclick_text = a_tag.get('onclick', '')
            id_match = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", onclick_text)
            mem_id = id_match.group(1) if id_match else nick

            # 2. 금액 및 타입(+/-) 정확히 파악
            row_text = row.get_text()
            if any(kw in row_text for kw in SYSTEM_KEYWORDS): continue
            
            m_plus = re.search(r'\+\s*([0-9,]+)', row_text)
            m_minus = re.search(r'-\s*([0-9,]+)', row_text)
            
            if m_plus and "에게" not in row_text:
                val = int(m_plus.group(1).replace(',', ''))
                giver_data.append({'name': nick, 'mem_id': mem_id, 'val': val})
                
            elif m_minus and "에게" in row_text:
                val = int(m_minus.group(1).replace(',', ''))
                quest_data.append({'name': nick, 'mem_id': mem_id, 'val': val})
                
        return {"donation": giver_data, "quest": quest_data}
    except Exception:
        return {"donation": [], "quest": []}

def get_storage_rankings():
    print("🔥 [FULL] 창고 랭킹 수집 시작 (고유 아이디 기반 + 무한로딩 방지)...")
    raw_giver = []
    raw_quest = []
    last_page_data = None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_storage_page, range(1, 201))
        for res in results:
            current_signature = str(res["donation"]) + str(res["quest"])
            if current_signature == last_page_data or (not res["donation"] and not res["quest"]):
                break 
            last_page_data = current_signature
            raw_giver.extend(res["donation"])
            raw_quest.extend(res["quest"])
            
    df_giver = pd.DataFrame(raw_giver).groupby(['mem_id', 'name'], as_index=False).sum().sort_values('val', ascending=False).head(50) if raw_giver else pd.DataFrame(columns=['mem_id', 'name', 'val'])
    df_quest = pd.DataFrame(raw_quest).groupby(['mem_id', 'name'], as_index=False).sum().sort_values('val', ascending=False).head(50) if raw_quest else pd.DataFrame(columns=['mem_id', 'name', 'val'])
    
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
