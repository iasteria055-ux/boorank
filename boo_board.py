import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import time
from datetime import datetime
import concurrent.futures

# --- 1. 기본 설정 ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- 2. [FAST 모드] 일퀘 달성자 수집 로직 ---
def fetch_board_page(page_num):
    """게시판 특정 페이지를 긁어오는 분신술(스레드) 함수"""
    # TODO: 와이고수 부우게시판 실제 URL로 변경하세요.
    url = f"https://ygosu.com/community/pan_boo/?page={page_num}" 
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    achievers = []
    # TODO: 선생님이 기존에 짜두신 '게시글/댓글/날짜' 긁어오는 로직을 여기에 넣습니다.
    # 예시: 7월 9일 이후 글만 필터링하여 게시글 1 + 댓글 20 확인
    # 달성자를 찾으면 아래 형식으로 리스트에 추가합니다.
    # achievers.append({
    #     "name": "유저닉네임", 
    #     "mem_id": "123456", 
    #     "profile_url": "프록시이미지주소"
    # })
    
    return achievers

def get_quest_achievers():
    print("🚀 [FAST 모드] 실시간 일퀘 달성자 수집 시작 (멀티스레딩)...")
    all_achievers = []
    
    # 분신술 10명을 소환해서 1페이지부터 10페이지까지 동시에 긁어옵니다. (속도 10배!)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        pages_to_scrape = range(1, 11) # 1~10페이지
        results = executor.map(fetch_board_page, pages_to_scrape)
        
        for result in results:
            all_achievers.extend(result)
            
    # 중복 제거 및 정렬 등 후처리 후 반환
    return all_achievers


# --- 3. [FULL 모드] 창고 기부왕/일퀘왕 수집 로직 ---
def fetch_storage_page(page_num):
    """창고 특정 페이지를 긁어오는 분신술(스레드) 함수"""
    # TODO: 와이고수 창고(Mineral Storage) 실제 URL로 변경하세요.
    url = f"https://ygosu.com/community/pan_boo/?mode=mineral_storage&page={page_num}"
    res = requests.get(url, headers=HEADERS)
    # TODO: 창고 긁어서 '닉네임 + 숫자' (기부왕), '닉네임 - 숫자' (일퀘왕) 분류하는 기존 로직
    return {"donation": [], "quest": []} # 임시 반환값

def get_storage_rankings():
    print("🔥 [FULL 모드] 창고 전체 랭킹 수집 시작 (멀티스레딩)...")
    donation_ranking = []
    quest_ranking = []
    
    # 분신술 15명을 소환해서 창고 첫 페이지부터 다 긁어옵니다.
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        pages_to_scrape = range(1, 51) # 1~50페이지 (필요시 조절)
        results = executor.map(fetch_storage_page, pages_to_scrape)
        
        for result in results:
            donation_ranking.extend(result["donation"])
            quest_ranking.extend(result["quest"])
            
    # TODO: 여기서 누적 금액 합산 및 순위(rank) 정렬 로직 추가
    return donation_ranking, quest_ranking


# --- 4. 메인 실행 (데이터 병합 및 JSON 저장) ---
def main():
    # 깃허브 액션에서 'python boo_board.py fast' 처럼 인자를 받아옴
    mode = sys.argv[1] if len(sys.argv) > 1 else 'fast'
    
    # 1. 기존 data.json 뼈대 준비 (파일이 없으면 새로 생성)
    data = {
        "updated_at": "",
        "quest_board": [],       # 일퀘 달성자
        "donation_ranking": [],  # 기부왕
        "quest_ranking": []      # 일퀘왕
    }
    
    # 기존 파일이 있다면 불러오기 (fast/full 서로 데이터를 덮어씌워 날아가지 않게 방어!)
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                pass
                
    # 2. 모드에 따라 데이터 갱신
    if mode == 'fast':
        data['quest_board'] = get_quest_achievers()
    elif mode == 'full':
        donation_data, quest_data = get_storage_rankings()
        data['donation_ranking'] = donation_data
        data['quest_ranking'] = quest_data

    # 3. 업데이트 시간 기록 (한국 시간 기준)
    data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 4. JSON 파일로 예쁘게 저장 (HTML 생성 코드는 완벽히 멸망시켰습니다!)
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ {mode} 모드 실행 완료! data.json 저장 성공!")

if __name__ == "__main__":
    main()
