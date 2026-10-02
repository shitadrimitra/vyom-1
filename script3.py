import sys

def modify_html():
    with open('e:/WEatherGPT/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    css_from = '''        .thought-line {
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
        }'''

    css_to = '''        #loading-thoughts-container {
            display: flex;
            flex-direction: column;
            gap: 0;
            margin-top: 8px;
            padding-left: 5px;
        }

        .thought-line {
            font-size: 0.95rem;
            color: var(--text-muted);
            display: flex;
            align-items: flex-start;
            gap: 12px;
            animation: fadeInThought 0.3s ease forwards;
            position: relative;
            padding-bottom: 15px;
        }

        /* The connecting vertical line */
        .thought-line:not(:last-child)::after {
            content: '';
            position: absolute;
            left: 5px;
            top: 20px;
            bottom: -2px;
            width: 1.5px;
            background: var(--glass-border);
        }

        .thought-line.active {
            color: var(--text-main);
            font-weight: 500;
        }

        .thought-line.done {
            opacity: 0.8;
        }

        .thought-icon {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-top: 4px;
            flex-shrink: 0;
            position: relative;
            z-index: 2;
            background: var(--bg-base);
        }

        .spinner-dot {
            border: 2px solid transparent;
            border-top-color: var(--primary);
            border-right-color: var(--primary);
            animation: thoughtSpin 0.8s linear infinite;
            background: transparent;
        }

        .glowing-dot {
            background: var(--primary);
            box-shadow: 0 0 8px var(--primary), 0 0 12px var(--glow-1);
            border: none;
        }
        
        @media (max-width: 650px) {
            .thought-line {
                font-size: 0.85rem;
                padding-bottom: 12px;
            }
            .thought-line:not(:last-child)::after {
                top: 18px;
            }
        }'''

    content = content.replace(css_from, css_to)

    js_from = '''        let loadingInterval;
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
        loadingInterval = setInterval(addThought, 1200);'''

    js_to = '''        let loadingInterval;
        let thoughtStep = 0;
        
        const allThoughts = [
            "Initializing secure connection to weather models...",
            "Querying numerical weather telemetry (GFS, ECMWF, ICON)...",
            "Fetching real-time atmospheric sensor data...",
            "Analyzing satellite imagery & radar telemetry...",
            "Cross-referencing historical climate anomalies...",
            "Applying AI forecasting heuristics...",
            "Validating local topography effects on wind shear...",
            "Calculating precise humidity and dew point spreads...",
            "Aggregating global cloud cover patterns...",
            "Evaluating barometric pressure trends...",
            "Checking marine buoys and ocean current data...",
            "Running localized precipitation probability models...",
            "Parsing upper-atmosphere jet stream vectors...",
            "Correlating temperature gradients with urban heat islands...",
            "Scanning for severe weather alerts in the region...",
            "Calibrating microclimate variables..."
        ];

        // Pick 4-6 random thoughts for variety, always end with synthesizing
        const numThoughts = Math.floor(Math.random() * 3) + 4;
        let selectedThoughts = [];
        let tempThoughts = [...allThoughts];
        for(let i=0; i<numThoughts; i++) {
            const r = Math.floor(Math.random() * tempThoughts.length);
            selectedThoughts.push(tempThoughts[r]);
            tempThoughts.splice(r, 1);
        }
        selectedThoughts.push("Synthesizing customized meteorological brief...");

        function addThought() {
            const container = document.getElementById("loading-thoughts-container");
            if (!container) return;
            
            const prevActive = container.querySelector('.thought-line.active');
            if (prevActive) {
                prevActive.classList.remove('active');
                prevActive.classList.add('done');
                const icon = prevActive.querySelector('.thought-icon');
                if (icon) {
                    icon.className = 'thought-icon glowing-dot';
                }
            }
            
            // Loop if taking too long
            if (thoughtStep >= selectedThoughts.length) {
                const r = Math.floor(Math.random() * allThoughts.length);
                selectedThoughts.push(allThoughts[r]);
            }

            const newThought = document.createElement('div');
            newThought.className = 'thought-line active';
            newThought.innerHTML = `<div class="thought-icon spinner-dot"></div> <div class="thought-text">${selectedThoughts[thoughtStep]}</div>`;
            container.appendChild(newThought);
            chatArea.scrollTop = chatArea.scrollHeight;
            
            thoughtStep++;
            // Dynamic typing speed: between 1s and 2.5s
            const nextTime = Math.random() * 1500 + 1000;
            loadingInterval = setTimeout(addThought, nextTime);
        }
        
        addThought();'''

    content = content.replace(js_from, js_to)

    content = content.replace('clearInterval(loadingInterval);', 'clearTimeout(loadingInterval);')

    with open('e:/WEatherGPT/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

modify_html()