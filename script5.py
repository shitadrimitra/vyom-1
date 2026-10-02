import sys

def modify_html():
    with open('e:/WEatherGPT/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace readAloud() with readAloud(this)
    content = content.replace('onclick="readAloud()"', 'onclick="readAloud(this)"')

    # Update readAloud function
    js_from = '''    function readAloud() {
        if (!latestReportText) return;
        
        const speakBtn = document.getElementById("speak-btn");
        if (currentAudio) currentAudio.pause();
        
        speakBtn.disabled = true;
        speakBtn.innerHTML = "⏳ Synthesizing...";
        
        currentAudio = new Audio(`/speak?text=${encodeURIComponent(latestReportText)}&language=${encodeURIComponent(document.getElementById("langDropdown").getAttribute("data-value"))}`);
        
        currentAudio.onplay = () => { speakBtn.innerHTML = "🔊 Playing Audio..."; };
        currentAudio.onended = () => { speakBtn.disabled = false; speakBtn.innerHTML = "🔊 Read Advisory Aloud"; };
        currentAudio.onerror = () => { speakBtn.disabled = false; speakBtn.innerHTML = "❌ Audio Failed"; };
        
        currentAudio.play();
    }'''

    js_to = '''    function readAloud(btn) {
        if (!latestReportText) return;
        
        if (currentAudio) currentAudio.pause();
        
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = "⏳ Synthesizing...";
        }
        
        currentAudio = new Audio(`/speak?text=${encodeURIComponent(latestReportText)}&language=${encodeURIComponent(document.getElementById("langDropdown").getAttribute("data-value"))}`);
        
        currentAudio.onplay = () => { if(btn) btn.innerHTML = "🔊 Playing Audio..."; };
        currentAudio.onended = () => { if(btn) { btn.disabled = false; btn.innerHTML = "🔊 Read Advisory Aloud"; } };
        currentAudio.onerror = () => { if(btn) { btn.disabled = false; btn.innerHTML = "❌ Audio Failed"; } };
        
        currentAudio.play().catch(e => {
            console.error("Audio playback failed", e);
            if(btn) { btn.disabled = false; btn.innerHTML = "❌ Audio Failed"; }
        });
    }'''

    content = content.replace(js_from, js_to)

    # Just to be extremely safe, we ensure display: flex is applied directly instead of via class to avoid any CSS conflicts for the fallback block.
    fallback_from = '''                        <div class="actions-row" id="actionsRow-${respId}" style="display: none; margin-top: 15px;">'''
    fallback_to = '''                        <div class="actions-row" id="actionsRow-${respId}" style="display: none; margin-top: 15px; flex-wrap: wrap; gap: 10px;">'''
    content = content.replace(fallback_from, fallback_to)

    with open('e:/WEatherGPT/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

modify_html()