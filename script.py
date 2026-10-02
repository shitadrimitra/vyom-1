import sys

def modify_html():
    with open('e:/WEatherGPT/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    css_to_insert = '''
        /* ===== VOICE SEARCH OVERLAY ===== */
        .voice-search-overlay {
            position: fixed;
            inset: 0;
            z-index: 2000;
            background: var(--bg-gradient);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.4s ease, visibility 0.4s ease;
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
        }

        .voice-search-overlay.active {
            opacity: 1;
            visibility: visible;
        }

        .voice-orb-container {
            position: relative;
            width: 250px;
            height: 250px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 40px;
            margin-top: 40px;
        }

        .voice-orb {
            position: absolute;
            width: 160px;
            height: 160px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, var(--primary), var(--glow-1), transparent);
            box-shadow: 0 0 60px var(--primary), inset 0 0 30px var(--glow-2);
            animation: orbFloat 4s ease-in-out infinite, orbPulse 2s ease-in-out infinite alternate;
            z-index: 10;
            opacity: 0.95;
        }

        .voice-orb::before {
            content: '';
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background: repeating-radial-gradient(circle at center, transparent 0, transparent 10px, rgba(255,255,255,0.1) 12px, transparent 15px);
            mix-blend-mode: overlay;
            animation: spin 20s linear infinite;
        }

        .voice-orb-ring {
            position: absolute;
            width: 160px;
            height: 160px;
            border-radius: 50%;
            border: 2px solid var(--primary);
            opacity: 0;
            z-index: 5;
        }

        .voice-orb-ring.ring-1 {
            animation: ringRipple 2s linear infinite;
        }

        .voice-orb-ring.ring-2 {
            animation: ringRipple 2s linear infinite 1s;
        }

        @keyframes orbFloat {
            0%, 100% { transform: translateY(0) scale(1); }
            50% { transform: translateY(-15px) scale(1.05); }
        }

        @keyframes orbPulse {
            0% { filter: brightness(1); box-shadow: 0 0 50px var(--primary); }
            100% { filter: brightness(1.2); box-shadow: 0 0 80px var(--primary), 0 0 120px var(--glow-1); }
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @keyframes ringRipple {
            0% { transform: scale(1); opacity: 0.8; }
            100% { transform: scale(2.8); opacity: 0; }
        }

        .voice-text {
            font-size: 1.3rem;
            color: var(--text-muted);
            margin-bottom: 20px;
            max-width: 80%;
            text-align: center;
            line-height: 1.6;
            min-height: 60px;
        }

        .voice-status {
            font-size: 1.2rem;
            font-weight: 500;
            color: var(--text-main);
            margin-bottom: 50px;
            animation: pulseText 1.5s infinite alternate;
        }

        @keyframes pulseText {
            from { opacity: 0.6; }
            to { opacity: 1; }
        }

        .mic-btn-large {
            width: 72px;
            height: 72px;
            border-radius: 50%;
            background: var(--primary);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            border: none;
            cursor: pointer;
            box-shadow: 0 0 0 0 var(--glow-1);
            animation: micBtnRipple 1.5s infinite;
        }

        .mic-btn-large svg {
            width: 32px;
            height: 32px;
        }

        @keyframes micBtnRipple {
            0% { box-shadow: 0 0 0 0 var(--glow-1); }
            100% { box-shadow: 0 0 0 30px transparent; }
        }

        .voice-close-btn {
            position: absolute;
            top: 25px;
            left: 25px;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: var(--glass-btn-bg);
            border: 1px solid var(--glass-border);
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            backdrop-filter: blur(10px);
            transition: 0.2s;
        }

        .voice-close-btn:hover {
            background: var(--glass-hover);
            color: var(--primary);
        }
'''

    content = content.replace('    </style>', css_to_insert + '\n    </style>')

    html_to_insert = '''
<!-- Voice Search Overlay -->
<div id="voiceSearchOverlay" class="voice-search-overlay">
    <button class="voice-close-btn" onclick="stopVoiceSearch()" title="Close Voice Search">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
    </button>

    <div style="position: absolute; top: 25px; background: var(--glass-btn-bg); border: 1px solid var(--glass-border); padding: 8px 18px; border-radius: 20px; font-weight: 600; font-size: 0.95rem; color: var(--primary); backdrop-filter: blur(10px);">
        Voice AI 1.0 <span style="background: var(--primary); color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-left: 6px;">Beta</span>
    </div>

    <div class="voice-orb-container">
        <div class="voice-orb"></div>
        <div class="voice-orb-ring ring-1"></div>
        <div class="voice-orb-ring ring-2"></div>
    </div>

    <div class="voice-text" id="voiceTextOutput">...</div>
    <div class="voice-status">I'm Listening</div>

    <button class="mic-btn-large" onclick="stopVoiceSearch()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="4" x2="12" y2="20"></line>
            <line x1="18" y1="8" x2="18" y2="16"></line>
            <line x1="6" y1="8" x2="6" y2="16"></line>
        </svg>
    </button>
</div>
'''

    content = content.replace('</body>', html_to_insert + '\n</body>')

    js_to_replace_from = '''            try {
                recognition.start();
                isListening = true;
                micBtn.classList.add('listening');
                input.placeholder = "Listening to full sentence... Speak now";
            } catch(e) {}'''

    js_to_replace_to = '''            try {
                recognition.start();
                isListening = true;
                micBtn.classList.add('listening');
                input.placeholder = "Listening to full sentence... Speak now";
                const overlay = document.getElementById('voiceSearchOverlay');
                if (overlay) overlay.classList.add('active');
                const voiceTextElem = document.getElementById('voiceTextOutput');
                if (voiceTextElem) voiceTextElem.innerText = "...";
            } catch(e) {}'''
    
    content = content.replace(js_to_replace_from, js_to_replace_to)

    js_result_from = '''            if (finalTranscript || interimTranscript) {
                input.value = finalTranscript + interimTranscript;
            }'''
    
    js_result_to = '''            if (finalTranscript || interimTranscript) {
                const fullText = finalTranscript + interimTranscript;
                input.value = fullText;
                const voiceTextElem = document.getElementById('voiceTextOutput');
                if (voiceTextElem) voiceTextElem.innerText = fullText;
            }'''

    content = content.replace(js_result_from, js_result_to)

    js_onerror_from = '''        recognition.onerror = () => {
            isListening = false;
            micBtn.classList.remove('listening');
            input.placeholder = "Ask anything...";
        };'''

    js_onerror_to = '''        recognition.onerror = () => {
            isListening = false;
            micBtn.classList.remove('listening');
            input.placeholder = "Ask anything...";
            const overlay = document.getElementById('voiceSearchOverlay');
            if (overlay) overlay.classList.remove('active');
        };'''

    content = content.replace(js_onerror_from, js_onerror_to)

    js_onend_from = '''        recognition.onend = () => {
            isListening = false;
            micBtn.classList.remove('listening');
            input.placeholder = "Ask anything...";
            
            if (input.value.trim().length > 0) {
                fetchWeather();
            }
        };'''

    js_onend_to = '''        recognition.onend = () => {
            isListening = false;
            micBtn.classList.remove('listening');
            input.placeholder = "Ask anything...";
            const overlay = document.getElementById('voiceSearchOverlay');
            if (overlay) overlay.classList.remove('active');
            
            if (input.value.trim().length > 0) {
                fetchWeather();
            }
        };'''

    content = content.replace(js_onend_from, js_onend_to)

    stop_func_code = '''    window.stopVoiceSearch = function() {
        if (isListening && recognition) {
            recognition.stop();
        } else {
            const overlay = document.getElementById('voiceSearchOverlay');
            if (overlay) overlay.classList.remove('active');
        }
    };
'''

    content = content.replace('const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;', stop_func_code + '\n    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;')

    with open('e:/WEatherGPT/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

modify_html()