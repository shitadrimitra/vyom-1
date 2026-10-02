import sys

def modify_html():
    with open('e:/WEatherGPT/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    js_from = '''            if (!t || Object.keys(t).length === 0) {
                chatArea.innerHTML += `
                    <div class="message">
                        <div class="message-role">WeatherGPT</div>
                        <div class="message-content" id="tw-${respId}"></div>
                    </div>`;
                streamTypewriter(document.getElementById(`tw-${respId}`), latestReportText, () => {
                    chatArea.scrollTop = chatArea.scrollHeight;
                });
                
                // Save to history
                currentChatMessages.push({ role: 'user', content: userDisplay });
                currentChatMessages.push({ role: 'assistant', content: latestReportText, telemetry: {} });
                saveChatToHistory(currentChatId, chatTitle, currentChatMessages);
                return;
            }'''

    js_to = '''            if (!t || Object.keys(t).length === 0) {
                chatArea.innerHTML += `
                    <div class="message">
                        <div class="message-role">WeatherGPT</div>
                        <div class="message-content" id="tw-${respId}"></div>
                        <div class="actions-row" id="actionsRow-${respId}" style="display: none; margin-top: 15px;">
                            <button class="audio-btn" id="speak-btn-${respId}" onclick="readAloud()">
                                <span>🔊</span> Read Advisory Aloud
                            </button>
                            <button class="audio-btn" onclick="downloadExecutiveBrief()">
                                <span>📄</span> Pdf Report
                            </button>
                        </div>
                    </div>`;
                streamTypewriter(document.getElementById(`tw-${respId}`), latestReportText, () => {
                    const speakBtn = document.getElementById(`speak-btn-${respId}`);
                    const actionsRow = document.getElementById(`actionsRow-${respId}`);
                    if (speakBtn) speakBtn.style.display = "flex";
                    if (actionsRow) actionsRow.style.display = "flex";
                    chatArea.scrollTop = chatArea.scrollHeight;
                });
                
                // Save to history
                currentChatMessages.push({ role: 'user', content: userDisplay });
                currentChatMessages.push({ role: 'assistant', content: latestReportText, telemetry: {} });
                saveChatToHistory(currentChatId, chatTitle, currentChatMessages);
                return;
            }'''

    content = content.replace(js_from, js_to)

    with open('e:/WEatherGPT/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

modify_html()