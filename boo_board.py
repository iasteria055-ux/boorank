<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOO BOARD DASHBOARD</title>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,900;1,900&display=swap');
        
        :root {
            --dj-purple: #351c61; 
            --dj-yellow: #f8c117; 
            --dj-orange: #f24b0f; /* 도네이션: 강렬한 레드-오렌지 */
            --dj-cyan: #00a3d2;   /* 리워드: 쨍한 스카이블루 */
            --dj-magenta: #d91c49; /* CLEAR: 딥 마젠타 */
            --dj-bg: #f4f5f8; /* 배경색 살짝 더 밝게 조정 */
            --dj-grid: #e8eaef; 
            --white: #ffffff; 
            --black: #111111;
            --dj-navy: #15162c;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body { 
            font-family: 'Pretendard', sans-serif; 
            background-color: var(--dj-bg); 
            /* 화면 바깥 배경에 은은한 45도 사선 패턴 적용 */
            background-image: repeating-linear-gradient(
                -45deg, 
                transparent, 
                transparent 15px, 
                rgba(53, 28, 97, 0.03) 15px, 
                rgba(53, 28, 97, 0.03) 30px
            );
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; padding: 2vh 10px; overflow: hidden;
        }
        
        .game-frame {
            width: 100%; max-width: 850px; height: 96vh;
            background-color: var(--white);
            background-image: 
                linear-gradient(var(--dj-grid) 1px, transparent 1px), 
                linear-gradient(90deg, var(--dj-grid) 1px, transparent 1px);
            background-size: 40px 40px;
            border: 10px solid var(--dj-purple);
            border-radius: 16px;
            position: relative; overflow: hidden;
            box-shadow: 0 15px 40px rgba(0,0,0,0.15), inset 0 0 0 4px #f0f2f5;
            display: flex; flex-direction: column;
        }

        /* -------------------------------------
           🔥 DJMAX 스타일 백그라운드 애니메이션 요소들
        -------------------------------------- */
        /* 화면 스캔라인 (오락기 모니터 느낌) */
        .scanlines {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,0) 50%, rgba(53,28,97,0.03) 50%, rgba(53,28,97,0.03));
            background-size: 100% 4px; z-index: 1; pointer-events: none;
        }

        /* 거대 백그라운드 텍스트 (RANK+ING 테마 참고) */
        .djmax-bg-text {
            position: absolute; top: 20%; right: -5%; z-index: 0;
            display: flex; flex-direction: column; pointer-events: none;
            transform: rotate(-10deg); opacity: 0.05;
        }
        .djmax-bg-text span {
            font-family: 'Montserrat', sans-serif; font-size: 180px; font-weight: 900; line-height: 0.8;
            letter-spacing: -10px; color: var(--dj-purple);
        }
        .djmax-bg-text .hollow {
            color: transparent; -webkit-text-stroke: 4px var(--dj-purple); margin-left: 80px;
            font-style: italic;
        }

        /* 둥둥 떠다니는 기하학 마크 (X, +, O) */
        .floating-sym { position: absolute; font-family: 'Montserrat', sans-serif; font-weight: 900; z-index: 1; opacity: 0.15; pointer-events: none; }
        .sym-1 { color: var(--dj-magenta); font-size: 120px; top: 5%; right: 10%; animation: float1 6s infinite alternate ease-in-out; }
        .sym-2 { color: var(--dj-cyan); font-size: 80px; bottom: 30%; left: 2%; transform: rotate(15deg); animation: float2 5s infinite alternate ease-in-out; }
        .sym-3 { color: var(--dj-yellow); font-size: 150px; top: 40%; left: 40%; animation: float3 8s infinite alternate ease-in-out; }
        
        @keyframes float1 { 0% { transform: translateY(0) rotate(0deg); } 100% { transform: translateY(30px) rotate(15deg); } }
        @keyframes float2 { 0% { transform: translateY(0) scale(1); } 100% { transform: translateY(-40px) scale(1.1); } }
        @keyframes float3 { 0% { transform: rotate(0deg) scale(0.9); } 100% { transform: rotate(45deg) scale(1.05); } }

        /* -------------------------------------
           HUD 오버레이
        -------------------------------------- */
        .hud-overlay {
            position: absolute; top: 15px; bottom: 15px; left: 15px; right: 15px;
            pointer-events: none; z-index: 5; border: 1px solid rgba(53, 28, 97, 0.1);
        }
        .hud-corner { position: absolute; width: 12px; height: 12px; border: 2px solid var(--dj-purple); }
        .hud-corner.tl { top: -2px; left: -2px; border-right: none; border-bottom: none; }
        .hud-corner.tr { top: -2px; right: -2px; border-left: none; border-bottom: none; }
        .hud-corner.bl { bottom: -2px; left: -2px; border-right: none; border-top: none; }
        .hud-corner.br { bottom: -2px; right: -2px; border-left: none; border-top: none; }

        .hud-top { position: absolute; top: 12px; left: 12px; right: 12px; display: flex; align-items: center; gap: 15px; }
        .hud-badge {
            border: 2px solid var(--dj-purple); padding: 3px 10px;
            font-family: 'Montserrat', sans-serif; font-size: 11px; font-weight: 900;
            color: var(--dj-purple); background: var(--white); letter-spacing: 1px;
        }
        .hud-line { flex: 1; height: 1px; background: var(--dj-purple); opacity: 0.2; }
        .hud-cross { font-family: 'Montserrat', sans-serif; font-size: 16px; font-weight: 900; color: var(--dj-magenta); }

        .eq-bars { display: flex; gap: 3px; align-items: flex-end; height: 14px; opacity: 0.8; }
        .eq-bar { width: 4px; background: var(--dj-cyan); border-radius: 2px; animation: eq-play 1s infinite alternate; }
        .eq-bar:nth-child(1) { background: var(--dj-magenta); animation-delay: 0.1s; }
        .eq-bar:nth-child(2) { background: var(--dj-yellow); animation-delay: 0.3s; }
        .eq-bar:nth-child(3) { background: var(--dj-cyan); animation-delay: 0.0s; }
        .eq-bar:nth-child(4) { background: var(--dj-orange); animation-delay: 0.4s; }
        .eq-bar:nth-child(5) { background: var(--dj-purple); animation-delay: 0.2s; }
        @keyframes eq-play { 0% { height: 4px; } 100% { height: 14px; } }

        .content-wrap { position: relative; padding: 45px 30px 45px; z-index: 10; display: flex; flex-direction: column; flex: 1; min-height: 0; }

        /* -------------------------------------
           상단 헤더 영역 
        -------------------------------------- */
        .top-header-area {
            display: flex; justify-content: space-between; align-items: flex-start;
            margin-bottom: 20px; gap: 20px;
        }
        
        .header-titles { 
            display: flex; flex-direction: column; 
            position: relative; padding-top: 10px; 
        }
        
        /* 세련된 팝아트 데코레이션 */
        .deco-dot-matrix {
            position: absolute; width: 60px; height: 60px; 
            background-image: radial-gradient(var(--dj-cyan) 20%, transparent 20%);
            background-size: 8px 8px;
            top: 5px; left: 160px; z-index: 0; opacity: 0.7;
        }
        .deco-star {
            position: absolute; width: 25px; height: 25px;
            background: var(--dj-magenta);
            clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
            top: 25px; left: 240px; z-index: 2;
            animation: spin 8s linear infinite;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        
        .deco-crosshair {
            position: absolute; width: 35px; height: 35px;
            border: 2px solid var(--dj-cyan); border-radius: 50%;
            top: -5px; left: 120px; z-index: 0; opacity: 0.6;
            display: flex; justify-content: center; align-items: center;
        }
        .deco-crosshair::before { content: ''; width: 2px; height: 100%; background: var(--dj-cyan); }
        .deco-crosshair::after { content: ''; width: 100%; height: 2px; background: var(--dj-cyan); position: absolute; }

        .deco-stripe-box {
            position: absolute; width: 70px; height: 20px;
            background: repeating-linear-gradient(-45deg, var(--dj-orange), var(--dj-orange) 4px, transparent 4px, transparent 8px);
            bottom: -5px; left: -10px; z-index: 0;
            transform: skewX(-15deg);
        }

        /* 변경됨: 서브타이틀 크기 및 여백 조정 */
        .top-subtitle {
            font-family: 'Montserrat', sans-serif; font-size: 14px; font-weight: 900;
            color: var(--dj-purple); letter-spacing: 2px; opacity: 0.8;
            display: flex; align-items: center; gap: 15px; 
            margin-bottom: 5px; margin-left: 5px; position: relative; z-index: 2;
        }
        .top-subtitle .barcode { font-size: 18px; letter-spacing: 3px; color: var(--dj-cyan); opacity: 0.8; }

        /* 변경됨: 타이틀 컨테이너 조정 */
        .header { position: relative; display: inline-block; cursor: default; z-index: 2; margin-top: -10px; padding-left: 10px; width: 100%;}
        
        /* 변경됨: 팝아트 컬러 블록 스케일업 및 재배치 */
        .block-cyan { position: absolute; width: 120px; height: 40px; background: var(--dj-cyan); top: 10px; left: -15px; z-index: 1; transform: skewX(-15deg); box-shadow: 4px 4px 0 var(--dj-purple); }
        .block-orange { position: absolute; width: 60px; height: 60px; background: var(--dj-orange); bottom: 10px; right: 20px; z-index: 1; border-radius: 50%; box-shadow: -4px 4px 0 var(--dj-purple); }
        
        /* 변경됨: BOO BOARD 글자 크기 극대화 및 RANK+ING 스타일 글리치/아웃라인 효과 적용 */
        .header h1 { 
            font-size: 110px; font-weight: 900; font-style: italic; font-family: 'Montserrat', sans-serif;
            text-transform: uppercase; line-height: 0.8; position: relative; z-index: 5;
            letter-spacing: -6px; color: var(--dj-yellow);
            text-shadow: 
                6px 6px 0 var(--dj-purple), 
                -4px -4px 0 var(--dj-cyan), /* 시안색 글리치 크게 */
                4px -4px 0 var(--dj-magenta), /* 마젠타색 글리치 크게 */
                10px 10px 0 rgba(0,0,0,0.15); /* 입체감 그림자 강화 */
            margin: 0; 
            transition: all 0.3s ease;
            display: flex; flex-direction: column;
        }
        
        /* 꽉 찬 느낌을 위해 줄 바꿈 간격 조정 */
        .header h1 span:first-child { margin-bottom: -5px; }

        .yt-box-mini { 
            width: 320px; height: 180px; flex-shrink: 0;
            background: var(--black); border: 4px solid var(--dj-purple); 
            box-shadow: 5px 5px 0 var(--dj-cyan), -2px -2px 0 var(--dj-magenta); 
            padding: 4px; overflow: hidden; transform: skewX(-2deg); 
            transition: transform 0.3s ease; position: relative; z-index: 10;
        }
        .yt-box-mini:hover { transform: skewX(0deg); box-shadow: 6px 6px 0 var(--dj-cyan), -3px -3px 0 var(--dj-magenta); }
        .yt-box-mini iframe { width: 100%; height: 100%; transform: skewX(2deg); display: block; transition: transform 0.3s ease; }
        .yt-box-mini:hover iframe { transform: skewX(0deg); }

        /* -------------------------------------
           탭 버튼
        -------------------------------------- */
        .tab-menu { display: flex; gap: 12px; margin-bottom: 15px; position: relative; z-index: 10;}
        .tab-btn { 
            flex: 1; padding: 12px; background: var(--white); 
            border: 3px solid var(--dj-purple); box-shadow: 4px 4px 0 var(--dj-purple); 
            font-size: 16px; font-weight: 900; font-style: italic; font-family: 'Montserrat', sans-serif;
            color: var(--dj-purple); cursor: pointer; transform: skewX(-8deg); transition: all 0.2s;
            position: relative; overflow: hidden;
        }
        .tab-btn span { display: inline-block; transform: skewX(8deg); position: relative; z-index: 2;}
        .tab-btn::before {
            content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
            background: repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(53, 28, 97, 0.05) 10px, rgba(53, 28, 97, 0.05) 20px);
            transition: left 0.3s; z-index: 1;
        }
        .tab-btn:hover::before { left: 0; }
        .tab-btn:hover { transform: skewX(-8deg) translateY(-2px); box-shadow: 5px 5px 0 var(--dj-magenta); color: var(--dj-magenta); border-color: var(--dj-magenta); }
        .tab-btn.active { background: var(--dj-purple); color: var(--dj-yellow); box-shadow: 4px 4px 0 var(--dj-cyan); border-color: var(--dj-purple); }
        .tab-btn#btnQuest.active { color: var(--dj-cyan); box-shadow: 4px 4px 0 var(--dj-cyan); }

        /* -------------------------------------
           랭킹 리스트 영역
        -------------------------------------- */
        .list-container { 
            display: flex; flex-direction: column; gap: 8px; 
            flex: 1; overflow-y: auto; padding-right: 10px; padding-bottom: 5px;
            position: relative; z-index: 10;
        }
        .list-container::-webkit-scrollbar { width: 8px; }
        .list-container::-webkit-scrollbar-track { background: rgba(53, 28, 97, 0.05); border-radius: 4px; }
        .list-container::-webkit-scrollbar-thumb { background: var(--dj-purple); border-radius: 4px; }

        .rank-row { 
            display: flex; align-items: center; background: var(--white); 
            border: 1px solid var(--dj-purple) !important; 
            border-left: 6px solid var(--dj-purple) !important;
            padding: 10px 15px; font-weight: 900; flex-shrink: 0;
            transform: skewX(-2deg); 
            transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.2s, background-color 0.2s;
            position: relative; overflow: hidden;
        }
        /* 호버 시 리듬게임 게이지가 차오르는 효과 */
        .rank-row::after {
            content: ''; position: absolute; right: 0; top: 0; height: 100%; width: 0;
            background: linear-gradient(90deg, transparent, rgba(53, 28, 97, 0.05));
            transition: width 0.3s ease; z-index: 0; pointer-events: none;
        }
        .rank-row:hover::after { width: 100%; }
        
        .giver-list .rank-row { border-left-color: var(--dj-orange) !important; box-shadow: 2px 2px 0 var(--dj-orange); }
        .quest-list .rank-row { border-left-color: var(--dj-cyan) !important; box-shadow: 2px 2px 0 var(--dj-cyan); }
        .daily-list .rank-row { border-left-color: var(--dj-magenta) !important; box-shadow: 2px 2px 0 var(--dj-magenta); }
        
        .rank-row:hover { transform: skewX(-2deg) translateX(5px) translateY(-1px); }
        .giver-list .rank-row:hover { box-shadow: -2px 4px 0 var(--dj-orange); background: #fffcf7; }
        .quest-list .rank-row:hover { box-shadow: -2px 4px 0 var(--dj-cyan); background: #f5ffff; }

        .rank-row.top-1 { background: repeating-linear-gradient(-45deg, #fff9e6, #fff9e6 8px, #ffffff 8px, #ffffff 16px); border-color: #d4af37 !important; border-left-color: #d4af37 !important; box-shadow: 2px 2px 0 #d4af37; }
        .rank-row.top-2 { background: repeating-linear-gradient(-45deg, #f5f5f5, #f5f5f5 8px, #ffffff 8px, #ffffff 16px); border-color: #a8a9ad !important; border-left-color: #a8a9ad !important; box-shadow: 2px 2px 0 #a8a9ad; }
        .rank-row.top-3 { background: repeating-linear-gradient(-45deg, #fff0e6, #fff0e6 8px, #ffffff 8px, #ffffff 16px); border-color: #cd7f32 !important; border-left-color: #cd7f32 !important; box-shadow: 2px 2px 0 #cd7f32; }

        .rank-num { font-size: 20px; color: #ccc; width: 45px; font-style: italic; font-family: 'Montserrat', sans-serif; white-space: nowrap; transform: skewX(2deg); position: relative; z-index: 2; }
        .rank-row.top-1 .rank-num { color: #d4af37; font-size: 20px; width: 75px; text-shadow: 1px 1px 0 rgba(0,0,0,0.1); }
        .rank-row.top-2 .rank-num { color: #a8a9ad; font-size: 20px; width: 75px; }
        .rank-row.top-3 .rank-num { color: #cd7f32; font-size: 20px; width: 75px; text-shadow: 1px 1px 0 rgba(0,0,0,0.1); }
        
        .rank-name { flex: 1; font-size: 16px; color: var(--dj-purple); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 10px; transform: skewX(2deg); position: relative; z-index: 2; }
        .rank-val { font-size: 18px; font-style: italic; font-family: 'Montserrat', sans-serif; text-align: right; white-space: nowrap; transform: skewX(2deg); position: relative; z-index: 2; }

        .val-daily { color: var(--dj-magenta); }
        .val-giver { color: var(--dj-orange); }
        .val-quest { color: var(--dj-cyan); }

        /* 🔥 은은한 팝아트 텍스트 배경 (콘텐츠 영역 뒤) */
        .content-bg-text {
            position: absolute;
            top: 40%; left: 50%;
            transform: translate(-50%, -50%) rotate(-5deg);
            font-size: 140px;
            font-weight: 900;
            font-family: 'Montserrat', sans-serif;
            color: transparent;
            -webkit-text-stroke: 2px rgba(53, 28, 97, 0.05); /* 아주 연한 보라색 테두리만 */
            white-space: nowrap;
            pointer-events: none;
            z-index: 1; /* 랭킹 리스트(z-index: 10)보다 뒤에 배치 */
            display: flex; flex-direction: column; align-items: center; line-height: 0.8;
            letter-spacing: -5px;
        }
        
        .content-bg-text .filled {
            color: rgba(248, 193, 23, 0.08); /* 노란색 약간 채움 */
            -webkit-text-stroke: 0;
            margin-right: 60px;
        }

        /* 하단 감사 인사 */
        .thank-you-msg {
            text-align: center; margin-top: auto; padding-top: 15px;
            font-family: 'Montserrat', sans-serif; font-size: 11px; font-weight: 900;
            color: var(--dj-purple); letter-spacing: 3px; opacity: 0.6;
            text-transform: uppercase; position: relative; z-index: 10;
        }

        /* -------------------------------------
           하단 전광판
        -------------------------------------- */
        .marquee-wrap { 
            position: absolute; bottom: 0; left: 0; width: 100%; height: 26px;
            background: var(--dj-navy); color: var(--dj-orange);
            display: flex; align-items: center; overflow: hidden; z-index: 20;
            font-family: 'Montserrat', sans-serif; font-size: 11px; font-weight: 900; letter-spacing: 2px;
            border-top: 1px solid var(--dj-purple);
        }
        .marquee-content { display: flex; white-space: nowrap; animation: scroll-left 15s linear infinite; }
        .marquee-content span { padding: 0 30px; }
        @keyframes scroll-left { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }

        @media (max-width: 700px) {
            .djmax-bg-text { display: none; } /* 모바일에서는 텍스트 숨김 */
            .sym-3 { display: none; }
            .game-frame { border-width: 6px; border-radius: 12px; }
            .content-wrap { padding: 30px 15px 35px; }
            .top-header-area { flex-direction: column; align-items: flex-start; gap: 15px; margin-bottom: 15px; }
            
            /* 모바일 타이틀 크기 조정 */
            .header-titles { padding-top: 5px; width: 100%;}
            .header h1 { font-size: 70px; letter-spacing:-3px; line-height: 0.85; text-shadow: 4px 4px 0 var(--dj-purple), -2px -2px 0 var(--dj-cyan), 2px -2px 0 var(--dj-magenta), 6px 6px 0 rgba(0,0,0,0.15); margin-top: 0;}
            .header h1 span:first-child { margin-bottom: 0px; }
            .top-subtitle { font-size: 11px; margin-bottom: 8px;}
            .top-subtitle .barcode { font-size: 14px;}
            .block-cyan { width: 70px; height: 25px; top: 0px; left: -5px; box-shadow: 2px 2px 0 var(--dj-purple);}
            .block-orange { width: 35px; height: 35px; bottom: 5px; right: 10px; box-shadow: -2px 2px 0 var(--dj-purple);}
            
            .deco-dot-matrix { left: 120px; top: 0px; width: 30px; height: 30px; background-size: 5px 5px; }
            .deco-crosshair { left: 90px; top: -10px; width: 25px; height: 25px; }
            .deco-star { left: 180px; top: 20px; width: 15px; height: 15px; }
            
            .yt-box-mini { width: 100%; height: 180px; transform: skewX(0); box-shadow: 4px 4px 0 var(--dj-cyan), -2px -2px 0 var(--dj-magenta); }
            .yt-box-mini iframe { transform: skewX(0); }
            
            .tab-menu { gap: 8px; margin-bottom: 12px; }
            .tab-btn { font-size: 13px; padding: 10px; border-width: 2px; box-shadow: 2px 2px 0 var(--dj-purple); transform: skewX(-5deg); }
            .tab-btn span { transform: skewX(5deg); }
            
            .rank-row { transform: skewX(0); padding: 8px 10px; border-left-width: 4px !important; box-shadow: 2px 2px 0 var(--dj-purple) !important; }
            .rank-num, .rank-name, .rank-val { transform: skewX(0); font-size: 14px; }
            .rank-num { width: 35px; }
            .rank-val { min-width: 70px; }
            .rank-row.top-1 .rank-num, .rank-row.top-2 .rank-num, .rank-row.top-3 .rank-num { font-size: 16px; width: 50px; }
        }
    </style>
</head>
<body>
    <div class="game-frame">
        <!-- DJMAX 감성 스캔라인 및 둥둥 떠다니는 기하학 데코레이션 -->
        <div class="scanlines"></div>
        
        <!-- RANK+ING 테마 참고: 거대 백그라운드 텍스트 -->
        <div class="djmax-bg-text">
            <span>RANK</span>
            <span class="hollow">+ING</span>
        </div>
        
        <div class="floating-sym sym-1">+</div>
        <div class="floating-sym sym-2">X</div>
        <div class="floating-sym sym-3">O</div>

        <div class="hud-overlay">
            <div class="hud-corner tl"></div><div class="hud-corner tr"></div>
            <div class="hud-corner bl"></div><div class="hud-corner br"></div>
            <div class="hud-top">
                <div class="hud-badge">MINERAL STORAGE</div>
                <div class="hud-line"></div>
                <div class="eq-bars">
                    <div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div><div class="eq-bar"></div>
                </div>
                <div class="hud-cross">+</div>
            </div>
        </div>

        <!-- 팝아트 텍스트 배경 추가 -->
        <div class="content-bg-text">
            <span>R A N K</span>
            <span class="filled">+ I N G</span>
        </div>

        <div class="content-wrap">
            <div class="top-header-area">
                <div class="header-titles">
                    <!-- 꽉 채운 팝아트 데코레이션 -->
                    <div class="deco-crosshair" style="top: 15px; left: 220px; width: 50px; height: 50px; border-width: 3px;"></div>
                    <div class="deco-dot-matrix" style="top: 10px; left: 280px; width: 80px; height: 80px; background-size: 10px 10px;"></div>
                    <div class="deco-star" style="top: 35px; left: 400px; width: 40px; height: 40px;"></div>
                    <div class="deco-stripe-box" style="bottom: -15px; left: 10px; width: 100px; height: 25px; border: 2px solid var(--dj-purple);"></div>
                    
                    <div class="top-subtitle">
                        <span>YGOSU</span>
                        <span class="barcode">|||| || ||| |</span>
                        <span>DATA ARCHIVE</span>
                    </div>
                    <div class="header">
                        <div class="block-cyan"></div>
                        <div class="block-orange"></div>
                        <h1><span class="bouncy-text">BOO</span><span class="bouncy-text" style="color: var(--white); text-shadow: 6px 6px 0 var(--dj-purple), -4px -4px 0 var(--dj-magenta), 4px -4px 0 var(--dj-cyan), 10px 10px 0 rgba(0,0,0,0.15);">BOARD</span></h1>
                    </div>
                </div>
                
                <div class="yt-box-mini">
                    <iframe src="https://www.youtube.com/embed/qZlu2j2SiBA?si=5sKTorKVU_Pt4Uso&autoplay=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
                </div>
            </div>

            <div class="tab-menu">
                <button class="tab-btn active" id="btnDaily" onclick="show('daily')"><span class="bouncy-text">DAILY QUEST</span></button>
                <button class="tab-btn" id="btnGiver" onclick="show('giver')"><span class="bouncy-text">DONATION</span></button>
                <button class="tab-btn" id="btnQuest" onclick="show('quest')"><span class="bouncy-text">REWARDS</span></button>
            </div>

            <div id="daily" class="list-container daily-list"></div>
            <div id="giver" class="list-container giver-list" style="display:none;"></div>
            <div id="quest" class="list-container quest-list" style="display:none;"></div>

            <div class="thank-you-msg">
                ★ THANK YOU FOR COMPLETING THE DAILY QUEST! ★
            </div>
        </div>

        <div class="marquee-wrap">
            <div class="marquee-content">
                <span>/// YGOSU BOO BOARD DATA ARCHIVE ///</span>
                <span>DAILY QUEST ACHIEVERS</span>
                <span>DONATION RANKING</span>
                <span>MINERAL REWARDS</span>
                <span>/// YGOSU BOO BOARD DATA ARCHIVE ///</span>
                <span>DAILY QUEST ACHIEVERS</span>
                <span>DONATION RANKING</span>
                <span>MINERAL REWARDS</span>
            </div>
        </div>
    </div>

    <script>
        function show(tab) {
            document.getElementById('daily').style.display = 'none';
            document.getElementById('giver').style.display = 'none';
            document.getElementById('quest').style.display = 'none';

            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

            if (tab === 'daily') {
                document.getElementById('daily').style.display = 'flex';
                document.getElementById('btnDaily').classList.add('active');
            } else if (tab === 'giver') {
                document.getElementById('giver').style.display = 'flex';
                document.getElementById('btnGiver').classList.add('active');
            } else if (tab === 'quest') {
                document.getElementById('quest').style.display = 'flex';
                document.getElementById('btnQuest').classList.add('active');
            }
        }

        // 랭킹 행 생성
        function createRows(dataList, typeClass, tabType) {
            if (!dataList || dataList.length === 0) {
                return '<div style="text-align:center; padding:20px; color:#999; font-weight:900; z-index:2; position:relative;">조건을 달성한 사람이 아직 없습니다.</div>';
            }

            var html = "";
            dataList.forEach(function(r, i) {
                var rankClass = "";
                var rankIcon = String(i + 1).padStart(2, '0');

                if (i === 0) { rankClass = "top-1"; rankIcon = "🥇 01"; }
                else if (i === 1) { rankClass = "top-2"; rankIcon = "🥈 02"; }
                else if (i === 2) { rankClass = "top-3"; rankIcon = "🥉 03"; }

                var nameHtml = '<span class="bouncy-text">' + r.name + '</span>';
                var valHtml = "";

                if (tabType === 'daily') {
                    valHtml = "CLEAR";
                } else {
                    valHtml = r.val.toLocaleString() + " MN";
                }

                html += '<div class="rank-row ' + rankClass + '">' +
                        '<div class="rank-num">' + rankIcon + '</div>' +
                        '<div class="rank-name">' + nameHtml + '</div>' +
                        '<div class="rank-val ' + typeClass + '"><span class="bouncy-text">' + valHtml + '</span></div>' +
                        '</div>';
            });
            return html;
        }

        // 데이터 로드
        function loadData() {
            fetch('data.json?t=' + new Date().getTime())
            .then(function(response) {
                if (!response.ok) throw new Error('네트워크 응답 실패');
                return response.json();
            })
            .then(function(data) {
                document.getElementById('daily').innerHTML = createRows(data.quest_board, "val-daily", "daily");
                document.getElementById('giver').innerHTML = createRows(data.donation_ranking, "val-giver", "giver");
                document.getElementById('quest').innerHTML = createRows(data.quest_ranking, "val-quest", "quest");
            })
            .catch(function(error) {
                console.error("데이터 로딩 오류:", error);
                document.getElementById('daily').innerHTML = '<div style="text-align:center; padding:20px; color:#999;">데이터를 불러올 수 없습니다.</div>';
                document.getElementById('giver').innerHTML = '<div style="text-align:center; padding:20px; color:#999;">데이터를 불러올 수 없습니다.</div>';
                document.getElementById('quest').innerHTML = '<div style="text-align:center; padding:20px; color:#999;">데이터를 불러올 수 없습니다.</div>';
            });
        }

        window.onload = function() {
            show('daily');
            loadData();
        };
    </script>
</body>
</html>
