import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import sys
import json
import os

# ==========================================
# 1. 설정 및 세션 초기화
# ==========================================
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
session = requests.Session()
session.headers.update(headers)

base_storage_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
board_url = "https://ygosu.com/board/pan_boo/?page="

pattern_giver = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
pattern_quest = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'
system_keywords = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]

# 실행 모드 판별 (GitHub Actions에서 인자를 전달함)
run_mode = sys.argv[1] if len(sys.argv) > 1 else 'fast'
data_file = 'mineral_data.json'

giver_list = []
quest_list = []

# ==========================================
# 2. 미네랄 창고 처리 (모드에 따라 분기)
# ==========================================
if run_mode == 'full' or not os.path.exists(data_file):
    print("🌕 [FULL 모드] 자정 업데이트: 미네랄 창고 전체 데이터를 수집합니다...")
    page = 1
    while True:
        try:
            res = session.get(f"{base_storage_url}{page}")
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            has_data = False
            for row in soup.find_all('tr'):
                row_text = " ".join(row.stripped_strings)
                if re.search(r'\d{2}-\d{2}-\d{2}', row_text):
                    has_data = True
                    
                # [기부왕]
                m_giver = re.search(pattern_giver, row_text)
                if m_giver:
                    mid_text = m_giver.group(1).strip()
                    val = int(m_giver.group(2).replace(',', ''))
                    if not any(kw in mid_text for kw in system_keywords):
                        parts = mid_text.split()
                        if parts:
                            nick = parts[0]
                            if nick not in ["운영자", "시스템", ""]:
                                mem_id = ""
                                a_tag = row.find('a', onclick=re.compile(r'show_nick_dropdown'))
                                if a_tag:
                                    m = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", a_tag['onclick'])
                                    if m: mem_id = m.group(1)
                                        
                                if nick == "XOXA": 
                                    nick = "초우코송이"
                                    mem_id = "705225"
                                giver_list.append({'name': nick, 'val': val, 'mem_id': mem_id})
                
                # [기존 일퀘왕]
                m_quest = re.search(pattern_quest, row_text)
                if m_quest:
                    mid_text = m_quest.group(1).strip()
                    val = int(m_quest.group(2).replace(',', ''))
                    if "에게" in mid_text:
                        parts = mid_text.split('에게')[0].split()
                        if parts:
                            nick = parts[-1]
                            if nick not in ["운영자", "시스템", ""]:
                                quest_list.append({'name': nick, 'val': val})
                                
            if not has_data or page > 5000:
                print(f"👉 총 {page-1}페이지까지 탐색을 완료했습니다.")
                break
            page += 1
        except Exception:
            break
            
    # 모은 데이터를 JSON 파일로 저장 (다음 30분 작업들이 빠르게 불러다 쓰도록)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump({'giver': giver_list, 'quest': quest_list}, f, ensure_ascii=False)
else:
    print("🌗 [FAST 모드] 30분 업데이트: 저장된 미네랄 창고 데이터를 빠르게 불러옵니다...")
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            giver_list = data.get('giver', [])
            quest_list = data.get('quest', [])
    except:
        print("데이터 불러오기 실패, 빈 상태로 진행합니다.")

# DataFrame 처리
df_giver = pd.DataFrame(giver_list)
if not df_giver.empty:
    df_giver = df_giver.groupby('name', as_index=False).agg({'val': 'sum', 'mem_id': 'first'}).sort_values('val', ascending=False).head(50)

df_quest = pd.DataFrame(quest_list)
if not df_quest.empty:
    df_quest = df_quest.groupby('name', as_index=False).sum().sort_values('val', ascending=False).head(50)


# ==========================================
# 3. 오늘자 게시판 활동 크롤링 (게시글 & 댓글) -> 이건 무조건 실행
# ==========================================
print("🚀 [공통] 오늘의 게시판 일퀘 활동을 추적합니다...")
daily_stats = {}
stop_crawling = False

for page in range(1, 16): 
    if stop_crawling: break
    try:
        res = session.get(f"{board_url}{page}")
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        trs = soup.select('tbody tr')
        
        if not trs: break
        
        for tr in trs:
            if tr.select_one('.notice') or tr.select_one('img[alt="공지"]'): continue
            
            date_td = tr.select_one('.date')
            if not date_td: continue
            date_text = date_td.text.strip()
            
            if '-' in date_text or '.' in date_text:
                stop_crawling = True
                break
                
            name_a = tr.select_one('.name a')
            if name_a and 'show_nick_dropdown' in name_a.get('onclick', ''):
                m = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", name_a['onclick'])
                if m:
                    mem_id = m.group(1)
                    nick = name_a.text.strip()
                    if mem_id not in daily_stats:
                        daily_stats[mem_id] = {'name': nick, 'posts': 0, 'comments': 0, 'profile_img': ''}
                    daily_stats[mem_id]['posts'] += 1
            
            post_a = tr.select_one('.tit a')
            if post_a:
                post_url = post_a['href']
                if not post_url.startswith('http'): post_url = "https://ygosu.com" + post_url
                try:
                    p_res = session.get(post_url)
                    p_res.encoding = 'utf-8'
                    p_soup = BeautifulSoup(p_res.text, 'html.parser')
                    for cmt_name in p_soup.select('.comment_list .name a'):
                        if 'show_nick_dropdown' in cmt_name.get('onclick', ''):
                            cm = re.search(r"show_nick_dropdown\([^,]+,\s*'([^']+)'", cmt_name['onclick'])
                            if cm:
                                c_mem_id = cm.group(1)
                                c_nick = cmt_name.text.strip()
                                if c_mem_id not in daily_stats:
                                    daily_stats[c_mem_id] = {'name': c_nick, 'posts': 0, 'comments': 0, 'profile_img': ''}
                                daily_stats[c_mem_id]['comments'] += 1
                except:
                    pass
    except:
        break

# ==========================================
# 4. 일퀘 완료자 필터링 & HTML 생성
# ==========================================
completed_users = []
for mem_id, data in daily_stats.items():
    if data['posts'] >= 1 and data['comments'] >= 20:
        try:
            m_res = session.get(f"https://ygosu.com/minilog/?m={mem_id}")
            m_res.encoding = 'utf-8'
            m_soup = BeautifulSoup(m_res.text, 'html.parser')
            img_tag = m_soup.select_one('.profile_img')
            
            if img_tag and img_tag.get('src'):
                img_url = img_tag['src']
                if not img_url.startswith('http'): img_url = "https://ygosu.com" + img_url
                data['profile_img'] = img_url
            else:
                data['profile_img'] = f"https://ui-avatars.com/api/?name={data['name']}&background=351c61&color=fff&bold=true"
        except:
            data['profile_img'] = f"https://ui-avatars.com/api/?name={data['name']}&background=351c61&color=fff&bold=true"
            
        data['mem_id'] = mem_id
        completed_users.append(data)

completed_users.sort(key=lambda x: (x['comments'], x['posts']), reverse=True)

total_active_users = len(daily_stats)
total_posts_today = sum(d['posts'] for d in daily_stats.values())
total_comments_today = sum(d['comments'] for d in daily_stats.values())
total_completed = len(completed_users)

def generate_rows(df, type_class):
    html = ""
    for i, r in df.reset_index(drop=True).iterrows():
        rank_class = ""
        rank_icon = f"{i+1:02d}"
        if i == 0:
            rank_class = "top-1"
            rank_icon = "🥇 01"
        elif i == 1:
            rank_class = "top-2"
            rank_icon = "🥈 02"
        elif i == 2:
            rank_class = "top-3"
            rank_icon = "🥉 03"
            
        mem_id = r.get('mem_id', '') if 'mem_id' in r else ''
        if mem_id:
            name_display = f'<a href="https://ygosu.com/minilog/?m={mem_id}" target="_blank" style="color: inherit; text-decoration: none;"><span class="bouncy-text">{r["name"]}</span></a>'
        else:
            name_display = f'<span class="bouncy-text">{r["name"]}</span>'
            
        html += f'''
        <div class="rank-row {rank_class}">
            <div class="rank-num">{rank_icon}</div>
            <div class="rank-name">{name_display}</div>
            <div class="rank-val {type_class}"><span class="bouncy-text">{r["val"]:,} MN</span></div>
        </div>'''
    return html

giver_html = generate_rows(df_giver if not df_giver.empty else pd.DataFrame(), "val-giver")
quest_html = generate_rows(df_quest if not df_quest.empty else pd.DataFrame(), "val-quest")

daily_html = ""
if completed_users:
    for i, u in enumerate(completed_users):
        transfer_url = f"https://ygosu.com/board/pan_boo/?mode=mineral_storage&mode2=withdraw&member={u['mem_id']}"
        daily_html += f'''
        <a href="{transfer_url}" class="daily-row-link" target="_self">
            <div class="daily-row completed">
                <div class="daily-rank">{i+1}</div>
                <img src="{u['profile_img']}" class="profile-img" alt="profile">
                <div class="daily-info">
                    <div class="daily-name">{u['name']}</div>
                    <div class="daily-stats-text">
                        <span class="stat-indicator"><span class="dot on"></span> 게시글 {u['posts']}/1 완료</span>
                        <span class="stat-indicator"><span class="dot on"></span> 댓글 {u['comments']}/20 완료</span>
                    </div>
                </div>
                <div class="action-btn">선물하기</div>
            </div>
        </a>
        '''
else:
    daily_html = '''
    <div style="text-align:center; padding: 40px; color:#888; font-weight:bold;">
        아직 오늘 일퀘를 완료한 유저가 없습니다.<br><br>게시글 1개, 댓글 20개를 달성해보세요!
    </div>
    '''

html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOO BOARD DASHBOARD</title>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,900;1,900&display=swap');
        
        :root {{
            --dj-purple: #351c61; --dj-yellow: #f8c117; --dj-orange: #ea5920; 
            --dj-cyan: #1ebfd4; --dj-magenta: #e62253; --dj-bg: #f2f3f7; 
            --dj-grid: #e8eaef; --white: #ffffff; --black: #111111;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{ 
            font-family: 'Pretendard', sans-serif; 
            background-color: var(--dj-bg); 
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; padding: 2vh 10px;
        }}
        
        .game-frame {{
            width: 100%; max-width: 850px; 
            background-color: var(--white);
            background-image: 
                linear-gradient(var(--dj-grid) 1px, transparent 1px), 
                linear-gradient(90deg, var(--dj-grid) 1px, transparent 1px);
            background-size: 40px 40px;
            border: 12px solid var(--dj-purple);
            border-radius: 20px;
            position: relative; overflow: hidden;
            box-shadow: 0 20px 50px rgba(0,0,0,0.1);
        }}

        .content-wrap {{ position: relative; padding: 40px 30px; z-index: 10; display: flex; flex-direction: column; }}

        .top-header-area {{
            display: flex; justify-content: space-between; align-items: flex-end;
            margin-bottom: 25px; gap: 20px;
        }}
        
        .header-titles {{ flex: 1; }}
        
        .top-subtitle {{
            font-family: 'Montserrat', sans-serif; font-size: 12px; font-weight: 900;
            color: var(--dj-purple); letter-spacing: 2px; opacity: 0.6;
            display: flex; align-items: center; gap: 12px; margin-bottom: 5px; margin-left: 5px;
        }}
        .top-subtitle .barcode {{ font-size: 14px; letter-spacing: 3px; color: var(--dj-cyan); opacity: 0.8; }}

        .header {{ position: relative; display: inline-block; cursor: default; }}
        .block-cyan {{ position: absolute; width: 50px; height: 30px; background: var(--dj-cyan); top: -10px; left: -10px; z-index: 1; }}
        .block-orange {{ position: absolute; width: 45px; height: 45px; background: var(--dj-orange); bottom: -5px; right: -15px; z-index: 1; }}
        
        .header h1 {{ 
            font-size: 68px; font-weight: 900; font-style: italic; font-family: 'Montserrat', sans-serif;
            text-transform: uppercase; line-height: 0.9; position: relative; z-index: 5;
            letter-spacing: -3px; color: var(--dj-yellow);
            text-shadow: 4px 4px 0 var(--dj-purple), 8px 8px 0 rgba(0,0,0,0.1);
            margin: 0;
        }}

        .yt-box-mini {{ 
            width: 320px; height: 180px; flex-shrink: 0;
            background: var(--black); border: 4px solid var(--dj-purple); 
            box-shadow: 6px 6px 0 rgba(53, 28, 97, 0.3), -3px -3px 0 var(--dj-cyan); 
            padding: 4px; overflow: hidden; transform: skewX(-2deg); 
        }}
        .yt-box-mini iframe {{ width: 100%; height: 100%; transform: skewX(2deg); display: block; }}

        .dashboard-grid {{
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            background: var(--black); border: 2px solid var(--dj-purple); border-radius: 8px;
            padding: 15px 10px; text-align: center; color: var(--white);
            box-shadow: 4px 4px 0 rgba(53, 28, 97, 0.2);
        }}
        .stat-card.highlight {{ border-color: var(--dj-yellow); box-shadow: 4px 4px 0 rgba(248, 193, 23, 0.3); }}
        .stat-title {{ font-size: 13px; color: #aaa; margin-bottom: 5px; font-weight: bold; }}
        .stat-value {{ font-size: 26px; font-weight: 900; color: var(--dj-cyan); font-family: 'Montserrat', sans-serif; }}
        .stat-card.highlight .stat-value {{ color: var(--dj-yellow); }}

        .tab-menu {{ display: flex; gap: 15px; margin-bottom: 20px; }}
        .tab-btn {{ 
            flex: 1; padding: 14px; background: var(--white); 
            border: 3px solid var(--dj-purple); box-shadow: 3px 3px 0 var(--dj-purple); 
            font-size: 16px; font-weight: 900; font-style: italic; font-family: 'Montserrat', sans-serif;
            color: var(--dj-purple); cursor: pointer; transform: skewX(-5deg); transition: all 0.2s;
        }}
        .tab-btn span {{ display: inline-block; transform: skewX(5deg); }}
        .tab-btn.active {{ background: var(--dj-purple); color: var(--white); box-shadow: 3px 3px 0 var(--dj-cyan); border-color: var(--dj-purple); }}
        .tab-btn#btnDaily.active {{ color: #00ff00; box-shadow: 3px 3px 0 #00ff00; }}

        .list-container {{ 
            display: flex; flex-direction: column; gap: 8px; 
            max-height: 450px; overflow-y: auto; padding-right: 10px; 
        }}
        
        .list-container::-webkit-scrollbar {{ width: 8px; }}
        .list-container::-webkit-scrollbar-track {{ background: rgba(53, 28, 97, 0.05); border-radius: 4px; }}
        .list-container::-webkit-scrollbar-thumb {{ background: var(--dj-purple); border-radius: 4px; }}

        .rank-row {{ 
            display: flex; align-items: center; background: var(--white); 
            border: 2px solid var(--dj-purple); border-left: 8px solid var(--dj-purple);
            padding: 10px 15px; font-weight: 900; flex-shrink: 0;
        }}
        .giver-list .rank-row {{ border-left-color: var(--dj-orange); }}
        .quest-list .rank-row {{ border-left-color: var(--dj-cyan); }}
        .rank-row.top-1 {{ background: linear-gradient(90deg, #fff9e6, #ffffff); border-color: #d4af37; border-left-color: #d4af37; }}
        .rank-row.top-2 {{ background: linear-gradient(90deg, #f5f5f5, #ffffff); border-color: #a8a9ad; border-left-color: #a8a9ad; }}
        .rank-row.top-3 {{ background: linear-gradient(90deg, #fff0e6, #ffffff); border-color: #cd7f32; border-left-color: #cd7f32; }}
        .rank-num {{ font-size: 20px; color: #ccc; width: 45px; font-style: italic; font-family: 'Montserrat', sans-serif; white-space: nowrap; }}
        .rank-row.top-1 .rank-num {{ color: #d4af37; font-size: 20px; width: 75px; }}
        .rank-row.top-2 .rank-num {{ color: #a8a9ad; font-size: 20px; width: 75px; }}
        .rank-row.top-3 .rank-num {{ color: #cd7f32; font-size: 20px; width: 75px; }}
        .rank-name {{ flex: 1; font-size: 16px; color: var(--dj-purple); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .rank-val {{ font-size: 18px; font-style: italic; font-family: 'Montserrat', sans-serif; text-align: right; white-space: nowrap; }}
        .val-giver {{ color: var(--dj-orange); }}
        .val-quest {{ color: var(--dj-cyan); }}

        .daily-list {{ background: #1a1a24; padding: 15px; border-radius: 12px; border: 2px solid var(--dj-purple); }}
        .daily-row-link {{ text-decoration: none; color: inherit; display: block; }}
        .daily-row {{ 
            display: flex; align-items: center; background: #222; 
            border: 2px solid #333; border-radius: 10px; padding: 12px; 
            margin-bottom: 8px; transition: all 0.2s;
        }}
        .daily-row.completed {{ border-color: #2e8b57; box-shadow: 0 0 10px rgba(46,139,87,0.2); }}
        .daily-row:hover {{ transform: translateX(5px); border-color: #00ff00; box-shadow: 0 0 12px rgba(0,255,0,0.3); }}
        
        .daily-rank {{ width: 30px; font-size: 18px; color: #777; font-weight: 900; font-family: 'Montserrat', sans-serif; font-style: italic; }}
        .profile-img {{ width: 45px; height: 45px; border-radius: 10px; object-fit: cover; margin-right: 15px; border: 2px solid #555; background: #fff; }}
        
        .daily-info {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
        .daily-name {{ font-size: 16px; font-weight: 900; color: #fff; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .daily-stats-text {{ font-size: 12px; color: #aaa; display: flex; gap: 10px; }}
        
        .stat-indicator {{ display: inline-flex; align-items: center; gap: 4px; }}
        .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #555; }}
        .dot.on {{ background: #00ff00; box-shadow: 0 0 5px #00ff00; }}
        
        .action-btn {{ 
            background: var(--dj-purple); color: #fff; padding: 8px 14px; 
            border-radius: 6px; font-size: 13px; font-weight: bold; border: 1px solid #555;
            transition: background 0.2s; white-space: nowrap;
        }}
        .daily-row:hover .action-btn {{ background: var(--dj-magenta); border-color: var(--dj-magenta); }}
        
        .bouncy-text {{
            display: inline-block;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), color 0.2s, text-shadow 0.2s;
        }}
        .bouncy-text:hover {{ transform: translateY(-3px) scale(1.05); cursor: default; text-shadow: 0 4px 8px rgba(0,0,0,0.15); }}
        
        @media (max-width: 700px) {{
            .content-wrap {{ padding: 25px 15px; }}
            .top-header-area {{ flex-direction: column; align-items: flex-start; gap: 15px; }}
            .header h1 {{ font-size: 50px; }}
            .yt-box-mini {{ width: 100%; height: 180px; transform: skewX(0); }}
            .yt-box-mini iframe {{ transform: skewX(0); }}
            
            .dashboard-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .stat-value {{ font-size: 22px; }}
            
            .tab-btn {{ font-size: 14px; padding: 10px; }}
            
            .daily-stats-text {{ flex-direction: column; gap: 2px; }}
            .action-btn {{ padding: 6px 10px; font-size: 11px; }}
            .profile-img {{ width: 35px; height: 35px; margin-right: 10px; }}
            .daily-name {{ font-size: 14px; }}
        }}
    </style>
</head>
<body>
    <div class="game-frame">
        <div class="content-wrap">
            
            <div class="top-header-area">
                <div class="header-titles">
                    <div class="top-subtitle">
                        <span>YGOSU</span>
                        <span class="barcode">|||| || ||| |</span>
                        <span>DAILY TRACKER</span>
                    </div>
                    <div class="header">
                        <div class="block-cyan"></div>
                        <div class="block-orange"></div>
                        <h1>BOO<br>BOARD</h1>
                    </div>
                </div>
                
                <div class="yt-box-mini">
                    <iframe src="https://www.youtube.com/embed/vnTFdNZQ0UQ?si=iRSunb6wWGX7SGp5&amp;start=25&autoplay=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
                </div>
            </div>

            <div class="dashboard-grid">
                <div class="stat-card highlight">
                    <div class="stat-title">일퀘 완료자</div>
                    <div class="stat-value">{total_completed}명</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">오늘 활동 인원</div>
                    <div class="stat-value">{total_active_users}명</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">오늘 전체 글</div>
                    <div class="stat-value">{total_posts_today}개</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">오늘 전체 댓글</div>
                    <div class="stat-value">{total_comments_today}개</div>
                </div>
            </div>

            <div class="tab-menu">
                <button class="tab-btn active" id="btnDaily" onclick="show('daily')"><span>DAILY QUEST</span></button>
                <button class="tab-btn" id="btnGiver" onclick="show('giver')"><span>DONATION</span></button>
                <button class="tab-btn" id="btnQuest" onclick="show('quest')"><span>ALL QUEST</span></button>
            </div>

            <div id="daily" class="list-container daily-list">
                {daily_html}
            </div>
            <div id="giver" class="list-container giver-list" style="display:none;">
                {giver_html}
            </div>
            <div id="quest" class="list-container quest-list" style="display:none;">
                {quest_html}
            </div>
            
        </div>
    </div>

    <script>
        function show(id) {{
            document.getElementById('daily').style.display = (id === 'daily') ? 'flex' : 'none';
            document.getElementById('giver').style.display = (id === 'giver') ? 'flex' : 'none';
            document.getElementById('quest').style.display = (id === 'quest') ? 'flex' : 'none';
            
            document.getElementById('btnDaily').className = (id === 'daily') ? 'tab-btn active' : 'tab-btn';
            document.getElementById('btnGiver').className = (id === 'giver') ? 'tab-btn active' : 'tab-btn';
            document.getElementById('btnQuest').className = (id === 'quest') ? 'tab-btn active' : 'tab-btn';
        }}
    </script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ 성공적으로 생성되었습니다!")
