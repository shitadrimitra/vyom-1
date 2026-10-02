import sys

def modify_html():
    with open('e:/WEatherGPT/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    css_to_insert = '''
        /* ===== AI THINKING ANIMATION ===== */
        .ai-thinking-badge {
            background: var(--glass-btn-bg);
            color: var(--primary);
            border: 1px solid var(--primary);
            padding: 2px 6px;
            border-radius: 6px;
            font-size: 0.65rem;
            margin-left: 8px;
            animation: badgePulse 1.5s infinite alternate;
        }

        .thought-line {
            font-size: 0.95rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            animation: fadeInThought 0.3s ease forwards;
        }

        .thought-line.active {
            color: var(--text-main);
            font-weight: 500;
        }

        .thought-spinner {
            width: 14px;
            height: 14px;
            border: 2px solid transparent;
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: thoughtSpin 0.8s linear infinite;
        }

        .thought-check {
            color: #10b981;
            font-size: 0.9rem;
            font-weight: bold;
        }

        @keyframes fadeInThought {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes badgePulse {
            from { opacity: 0.6; box-shadow: 0 0 2px var(--primary); }
            to { opacity: 1; box-shadow: 0 0 8px var(--primary); }
        }

        @keyframes thoughtSpin {
            to { transform: rotate(360deg); }
        }
'''

    content = content.replace('/* ===== VOICE SEARCH OVERLAY ===== */', css_to_insert + '\n        /* ===== VOICE SEARCH OVERLAY ===== */')

    js_from = '''        // Append user message (not replace)
        chatArea.innerHTML += `
            <div class="message">
                <div class="message-role">You</div>
                <div class="message-content">${escapeHtml(userDisplay)}</div>
            </div>
            <div class="message" id="loading-msg">
                <div class="message-role">WeatherGPT</div>
                <div class="message-content"><em>Querying numerical weather models and atmospheric sensors...</em></div>
            </div>`;
        
        chatArea.scrollTop = chatArea.scrollHeight;

        const analyzeBtn = document.getElementById("analyzeBtn");
        analyzeBtn.classList.add("loading"); 
        
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        try {'''

    js_to = '''        // Append user message (not replace)
        chatArea.innerHTML += `
            <div class="message">
                <div class="message-role">You</div>
                <div class="message-content">${escapeHtml(userDisplay)}</div>
            </div>
            <div class="message" id="loading-msg">
                <div class="message-role">WeatherGPT <span class="ai-thinking-badge">Thinking...</span></div>
                <div class="message-content" id="loading-thoughts-container">
                </div>
            </div>`;
        
        chatArea.scrollTop = chatArea.scrollHeight;

        const analyzeBtn = document.getElementById("analyzeBtn");
        analyzeBtn.classList.add("loading"); 
        
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        let loadingInterval;
        let thoughtStep = 0;
        const thoughts = [
            "Initializing secure connection to weather models...",
            "Querying numerical weather telemetry (GFS, ECMWF, ICON)...",
            "Fetching real-time atmospheric sensor data...",
            "Analyzing satellite imagery & radar telemetry...",
            "Cross-referencing historical climate anomalies...",
            "Applying AI forecasting heuristics...",
            "Synthesizing customized meteorological brief..."
        ];

        function addThought() {
            const container = document.getElementById("loading-thoughts-container");
            if (!container) return;
            
            const prevActive = container.querySelector('.thought-line.active');
            if (prevActive) {
                prevActive.classList.remove('active');
                prevActive.innerHTML = `<span class="thought-check">✓</span> ${thoughts[thoughtStep - 1]}`;
            }
            
            if (thoughtStep < thoughts.length) {
                const newThought = document.createElement('div');
                newThought.className = 'thought-line active';
                newThought.innerHTML = `<div class="thought-spinner"></div> ${thoughts[thoughtStep]}`;
                container.appendChild(newThought);
                chatArea.scrollTop = chatArea.scrollHeight;
                thoughtStep++;
            }
        }
        
        addThought();
        loadingInterval = setInterval(addThought, 1200);

        try {'''

    content = content.replace(js_from, js_to)

    js_clear_from = '''            const res = await fetch(url);
            const data = await res.json();
            
            const loadingMsg = document.getElementById("loading-msg");
            if (loadingMsg) loadingMsg.remove();'''

    js_clear_to = '''            const res = await fetch(url);
            const data = await res.json();
            
            clearInterval(loadingInterval);
            const loadingMsg = document.getElementById("loading-msg");
            if (loadingMsg) loadingMsg.remove();'''

    content = content.replace(js_clear_from, js_clear_to)

    js_catch_from = '''        } catch (err) {
            console.error("Fetch failed", err);
            const loadingMsg = document.getElementById("loading-msg");
            if (loadingMsg) {
                loadingMsg.querySelector('.message-content').innerHTML = '<em style="color:var(--alert-text);">Connection failed. Please check your network and try again.</em>';
            }
        } finally {'''

    js_catch_to = '''        } catch (err) {
            console.error("Fetch failed", err);
            clearInterval(loadingInterval);
            const loadingMsg = document.getElementById("loading-msg");
            if (loadingMsg) {
                loadingMsg.querySelector('.message-content').innerHTML = '<em style="color:var(--alert-text);">Connection failed. Please check your network and try again.</em>';
            }
        } finally {'''

    content = content.replace(js_catch_from, js_catch_to)

    with open('e:/WEatherGPT/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

modify_html()