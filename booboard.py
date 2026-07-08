import requests
from bs4 import BeautifulSoup
import re
import pandas as pd


# ==========================================
# 1. 설정
# ==========================================
base_url = "https://ygosu.com/board/pan_boo/?mode=mineral_storage&page="
max_pages = 109
headers = {"User-Agent": "Mozilla/5.0"}

giver_list = []
quest_list = []

pattern_giver = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)\+\s*([0-9,]+)'
pattern_quest = r'\d{2}-\d{2}-\d{2}\s*\([월화수목금토일]\)\s*\d{2}:\d{2}\s*(.*?)-\s*([0-9,]+)'
system_keywords = ["게시물", "댓글", "출석", "이벤트", "추천", "복권", "환전", "시스템"]

print("데이터 수집을 시작합니다...")

# ==========================================
# 2. 데이터 크롤링
# ==========================================
for page in range(1, max_pages + 1):
    url = f"{base_url}{page}"
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        for row in soup.find_all('tr'):
            row_text = " ".join(row.stripped_strings)

            # [기부왕] 로직
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
                            giver_list.append({'name': nick, 'val': val})

            # [일퀘왕] 로직
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
    except Exception as e:
        pass

# 합산 및 정렬 (상위 50명)
df_giver = pd.DataFrame(giver_list).groupby('name', as_index=False).sum().sort_values('val', ascending=False).head(50)
df_quest = pd.DataFrame(quest_list).groupby('name', as_index=False).sum().sort_values('val', ascending=False).head(50)

# ==========================================
# 3. HTML 생성 (디자인 피드백 반영 완료)
# ==========================================
def generate_rows(df, type_class):
    html = ""
    for i, r in df.reset_index(drop=True).iterrows():
        rank_class = ""
        rank_icon = f"{i+1:02d}"

        # Top 3 특별 강조
        if i == 0:
            rank_class = "top-1"
            rank_icon = "🥇 1ST"
        elif i == 1:
            rank_class = "top-2"
            rank_icon = "🥈 2ND"
        elif i == 2:
            rank_class = "top-3"
            rank_icon = "🥉 3RD"

        html += f'''
        <div class="rank-row {rank_class}">
            <div class="rank-num">{rank_icon}</div>
            <div class="rank-name"><span class="bouncy-text">{r["name"]}</span></div>
            <div class="rank-val {type_class}"><span class="bouncy-text">{r["val"]:,} MN</span></div>
        </div>'''
    return html

giver_html = generate_rows(df_giver, "val-giver")
quest_html = generate_rows(df_quest, "val-quest")

html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOO BOARD</title>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,900;1,900&display=swap');

        :root {{
            --dj-purple: #351c61; --dj-yellow: #f8c117; --dj-orange: #ea5920;
            --dj-cyan: #1ebfd4; --dj-magenta: #e62253; --dj-bg: #f2f3f7;
            --dj-grid: #e8eaef; --white: #ffffff; --black: #111111;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        /* 외부 여백 화이트 톤으로 변경 */
        body {{
            font-family: 'Pretendard', sans-serif;
            background-color: var(--dj-bg);
            display: flex; justify-content: center; align-items: center;
            height: 100vh; padding: 2vh 10px; overflow: hidden;
        }}

        /* 메인 프레임 테두리 솔리드 딥 퍼플 적용 */
        .game-frame {{
            width: 100%; max-width: 800px; height: 100%;
            display: flex; flex-direction: column;
            background-color: var(--white);
            background-image:
                linear-gradient(var(--dj-grid) 1px, transparent 1px),
                linear-gradient(90deg, var(--dj-grid) 1px, transparent 1px);
            background-size: 40px 40px;
            border: 12px solid var(--dj-purple);
            border-radius: 20px;
            position: relative; overflow: hidden;
            box-shadow: 0 20px 50px rgba(0,0,0,0.1), inset 0 0 0 3px #f0f2f5;
        }}

        /* 이퀄라이저 (빈 공간 채우기) */
        .eq-bars {{
            position: absolute; top: 50px; right: 40px;
            display: flex; gap: 4px; align-items: flex-end; height: 30px;
            z-index: 5; opacity: 0.7;
        }}
        .eq-bar {{ width: 6px; background: var(--dj-cyan); border-radius: 3px; animation: eq-play 1s infinite alternate; }}
        .eq-bar:nth-child(1) {{ background: var(--dj-magenta); animation-delay: 0.1s; }}
        .eq-bar:nth-child(2) {{ background: var(--dj-yellow); animation-delay: 0.3s; }}
        .eq-bar:nth-child(3) {{ background: var(--dj-cyan); animation-delay: 0.0s; }}
        .eq-bar:nth-child(4) {{ background: var(--dj-orange); animation-delay: 0.4s; }}
        .eq-bar:nth-child(5) {{ background: var(--dj-purple); animation-delay: 0.2s; }}

        @keyframes eq-play {{
            0% {{ height: 5px; }}
            100% {{ height: 30px; }}
        }}

        .content-wrap {{ position: relative; padding: 40px; z-index: 10; display: flex; flex-direction: column; flex: 1; min-height: 0; }}

        /* 타이틀 팝한 컬러 & 백그라운드 블록 */
        .header {{ margin-bottom: 25px; position: relative; z-index: 10; display: inline-block; cursor: default; align-self: flex-start; flex-shrink: 0; }}

        /* 스카이블루 사각형 */
        .block-cyan {{ position: absolute; width: 50px; height: 30px; background: var(--dj-cyan); top: -10px; left: -10px; z-index: 1; }}
        /* 오렌지 사각형 */
        .block-orange {{ position: absolute; width: 45px; height: 45px; background: var(--dj-orange); bottom: -5px; right: -15px; z-index: 1; }}
        /* 깔끔한 세로 장식선 */
        .block-lines {{ position: absolute; width: 60px; height: 15px; background: repeating-linear-gradient(90deg, var(--dj-purple), var(--dj-purple) 2px, transparent 2px, transparent 6px); top: 15px; right: -70px; z-index: 1; opacity: 0.4; }}

        .header h1 {{
            font-size: 76px; font-weight: 900; font-style: italic; font-family: 'Montserrat', sans-serif;
            text-transform: uppercase; line-height: 0.9; position: relative; z-index: 5;
            letter-spacing: -3px;
            color: var(--dj-yellow);
            text-shadow: 4px 4px 0 var(--dj-purple), 8px 8px 0 rgba(0,0,0,0.1);
        }}
        .header h1 .bouncy-text:hover {{ transform: translateY(-4px) scale(1.02) rotate(-2deg); }}

        .yt-box {{
            background: var(--black); border: 4px solid var(--dj-purple);
            box-shadow: 8px 8px 0 rgba(53, 28, 97, 0.3), -4px -4px 0 var(--dj-cyan);
            margin-bottom: 30px; padding: 4px; overflow: hidden; position: relative; z-index: 10; flex-shrink: 0;
            transform: skewX(-2deg);
        }}
        .yt-box iframe {{ transform: skewX(2deg); display: block; }}

        /* 탭 메뉴 */
        .tab-menu {{ display: flex; gap: 20px; margin-bottom: 25px; position: relative; z-index: 10; flex-shrink: 0; }}
        .tab-btn {{
            flex: 1; padding: 14px; background: var(--white);
            border: 3px solid var(--dj-purple); box-shadow: 4px 4px 0 var(--dj-purple);
            font-size: 20px; font-weight: 900; font-style: italic; font-family: 'Montserrat', sans-serif;
            color: var(--dj-purple); cursor: pointer; transform: skewX(-10deg); transition: all 0.2s; position: relative; overflow: hidden;
        }}
        .tab-btn span {{ display: inline-block; transform: skewX(10deg); }}
        .tab-btn:hover {{ transform: skewX(-10deg) translateY(-2px); box-shadow: 6px 6px 0 var(--dj-magenta); color: var(--dj-magenta); border-color: var(--dj-magenta); }}
        .tab-btn:active {{ transform: skewX(-10deg) translate(2px, 2px); box-shadow: 2px 2px 0 var(--dj-purple); }}
        .tab-btn.active {{ background: var(--dj-purple); color: var(--dj-yellow); box-shadow: 4px 4px 0 var(--dj-yellow); border-color: var(--dj-purple); }}
        .tab-btn#btnQuest.active {{ color: var(--dj-cyan); box-shadow: 4px 4px 0 var(--dj-cyan); }}

        /* 리스트 영역 */
        .list-container {{
            display: flex; flex-direction: column; gap: 10px; position: relative; z-index: 10;
            flex: 1; min-height: 0; overflow-y: auto; padding-right: 15px;
        }}

        .list-container::-webkit-scrollbar {{ width: 8px; }}
        .list-container::-webkit-scrollbar-track {{ background: rgba(53, 28, 97, 0.05); border-radius: 4px; }}
        .list-container::-webkit-scrollbar-thumb {{ background: var(--dj-purple); border-radius: 4px; }}

        .rank-row {{
            display: flex; align-items: center; background: var(--white);
            border: 2px solid var(--dj-purple); border-left: 8px solid var(--dj-purple);
            padding: 12px 15px; font-weight: 900; transition: all 0.2s; flex-shrink: 0; position: relative;
        }}
        .giver-list .rank-row {{ border-left-color: var(--dj-orange); }}
        .quest-list .rank-row {{ border-left-color: var(--dj-cyan); }}
        .rank-row:hover {{ transform: translateX(6px); box-shadow: -2px 5px 0 rgba(53, 28, 97, 0.2); background: #fdfdfd; }}

        /* TOP 3 특별 디자인 */
        .rank-row.top-1 {{ background: linear-gradient(90deg, #fff9e6, #ffffff); border-color: #d4af37; border-left-color: #d4af37; box-shadow: 0 0 10px rgba(212, 175, 55, 0.3); }}
        .rank-row.top-1 .rank-num {{ color: #d4af37; font-size: 26px; text-shadow: 1px 1px 0 rgba(0,0,0,0.1); width: 85px; }}
        .rank-row.top-2 {{ background: linear-gradient(90deg, #f5f5f5, #ffffff); border-color: #a8a9ad; border-left-color: #a8a9ad; }}
        .rank-row.top-2 .rank-num {{ color: #a8a9ad; font-size: 22px; width: 80px; }}
        .rank-row.top-3 {{ background: linear-gradient(90deg, #fff0e6, #ffffff); border-color: #cd7f32; border-left-color: #cd7f32; }}
        .rank-row.top-3 .rank-num {{ color: #cd7f32; font-size: 20px; width: 75px; }}

        .rank-num {{ font-size: 22px; color: #ccc; width: 45px; font-style: italic; font-family: 'Montserrat', sans-serif; }}
        .rank-name {{ flex: 1; font-size: 18px; color: var(--dj-purple); }}
        .rank-val {{ font-size: 19px; font-style: italic; font-family: 'Montserrat', sans-serif; text-align: right; }}

        .bouncy-text {{ display: inline-block; transition: transform 0.2s; }}
        .rank-row:hover .bouncy-text {{ transform: scale(1.05); }}

        .val-giver {{ color: var(--dj-orange); }}
        .val-quest {{ color: var(--dj-cyan); }}
    </style>
</head>
<body>
    <div class="game-frame">

        <!-- 이퀄라이저 장식 -->
        <div class="eq-bars">
            <div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div>
        </div>

        <div class="content-wrap">
            <div class="header">
                <div class="block-cyan"></div>
                <div class="block-orange"></div>
                <div class="block-lines"></div>
                <h1><span class="bouncy-text">BOO</span><br><span class="bouncy-text">BOARD</span></h1>
            </div>

            <div class="yt-box">
                <iframe width="100%" height="200" src="https://www.youtube.com/embed/vnTFdNZQ0UQ?si=iRSunb6wWGX7SGp5&amp;start=25&autoplay=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
            </div>

            <div class="tab-menu">
                <button class="tab-btn active" id="btnGiver" onclick="show('giver')"><span>DONATION</span></button>
                <button class="tab-btn" id="btnQuest" onclick="show('quest')"><span>QUEST</span></button>
            </div>

            <div id="giver" class="list-container giver-list">
                {giver_html}
            </div>

            <div id="quest" class="list-container quest-list" style="display:none;">
                {quest_html}
            </div>
        </div>
    </div>

    <script>
        function show(id) {{
            document.getElementById('giver').style.display = (id === 'giver') ? 'flex' : 'none';
            document.getElementById('quest').style.display = (id === 'quest') ? 'flex' : 'none';
            document.getElementById('btnGiver').className = (id === 'giver') ? 'tab-btn active' : 'tab-btn';
            document.getElementById('btnQuest').className = (id === 'quest') ? 'tab-btn active' : 'tab-btn';
        }}
    </script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ 완성! 코랩에서 'index.html'을 다운로드하세요. 피드백 주신 디자인 개선사항이 모두 적용되었습니다.")
