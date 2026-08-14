window.AiAgentPage = {
    render: () => {
        return `
            <div class="ai-agent-page" style="display: flex; flex-direction: column; flex: 1; min-height: 0; height: calc(100vh - 190px); gap: 14px;">
                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; background: #141a29; padding: 14px 20px; border-radius: 12px; border: 1px solid #232d42; flex-shrink: 0;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);">
                            <span style="font-size: 18px;">✨</span>
                        </div>
                        <div>
                            <h2 style="margin: 0; font-size: 16px; color: #fff; font-weight: 700;">JobPilot Autonomous AI Agent</h2>
                            <p style="margin: 2px 0 0 0; font-size: 12px; color: #94a3b8;">Give instructions in plain English to change settings, apply to jobs, or generate custom cover letters.</p>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <button id="ai-change-settings-mode-btn" style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(139, 92, 246, 0.2)); border: 1px solid #f59e0b60; color: #fbbf24; font-size: 12px; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 6px; transition: all 0.2s;" onmouseover="this.style.borderColor='#fbbf24'; this.style.transform='translateY(-1px)'" onmouseout="this.style.borderColor='#f59e0b60'; this.style.transform='none'">
                            <span>⚙️ Change Settings via AI</span>
                        </button>
                        <button id="ai-clear-chat-btn" style="background: transparent; border: 1px solid #232d42; color: #94a3b8; font-size: 12px; padding: 6px 12px; border-radius: 6px; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.borderColor='#ef4444'; this.style.color='#ef4444'" onmouseout="this.style.borderColor='#232d42'; this.style.color='#94a3b8'">Clear Chat</button>
                        <span style="font-size: 11px; color: #10b981; background: #10b98115; border: 1px solid #10b98130; padding: 4px 10px; border-radius: 20px; font-weight: 600; display: flex; align-items: center; gap: 5px;">
                            <span style="width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
                            Llama-3.3-70B Active
                        </span>
                    </div>
                </div>

                <!-- Chat & Action Feed -->
                <div id="ai-chat-stream" style="flex: 1; min-height: 250px; background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 18px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px;">
                    <!-- Populated dynamically from saved chatHistory -->
                </div>

                <!-- Prompt Input Bar -->
                <div style="background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 10px 14px; display: flex; flex-direction: column; gap: 6px; flex-shrink: 0;">
                    <!-- Mode Indicator Pill (Hidden by default) -->
                    <div id="ai-mode-indicator" style="display: none; align-items: center; justify-content: space-between; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; padding: 4px 10px; font-size: 11px; color: #fbbf24;">
                        <div style="display: flex; align-items: center; gap: 6px; font-weight: 600;">
                            <span>⚙️ Settings Update Mode Active</span>
                            <span style="color: #cbd5e1; font-weight: normal;">— Tell AI what locations, roles, or preferences to update</span>
                        </div>
                        <button id="ai-cancel-mode-btn" style="background: transparent; border: none; color: #94a3b8; font-size: 12px; cursor: pointer;" title="Cancel settings mode">✕ Cancel</button>
                    </div>

                    <div style="display: flex; gap: 10px; align-items: center;">
                        <input type="text" id="ai-prompt-input" placeholder="Give instruction to AI (e.g. 'Change my location to London and add React Developer', 'Apply to 5 jobs on LinkedIn')..." style="flex-grow: 1; padding: 11px 14px; background: #0c101a; border: 1px solid #232d42; color: #fff; border-radius: 8px; font-size: 13px; outline: none; transition: border-color 0.2s;" onfocus="this.style.borderColor='#3b82f6'" onblur="this.style.borderColor='#232d42'">
                        <button id="ai-send-btn" class="btn btn-primary" style="display: flex; align-items: center; gap: 6px; padding: 11px 18px; font-weight: 600; font-size: 13px; border-radius: 8px; flex-shrink: 0;">
                            <span>Execute</span>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    init: () => {
        const stream = document.getElementById('ai-chat-stream');
        const input = document.getElementById('ai-prompt-input');
        const sendBtn = document.getElementById('ai-send-btn');
        const clearBtn = document.getElementById('ai-clear-chat-btn');
        const changeSettingsBtn = document.getElementById('ai-change-settings-mode-btn');
        const modeIndicator = document.getElementById('ai-mode-indicator');
        const cancelModeBtn = document.getElementById('ai-cancel-mode-btn');

        let isSettingsMode = false;

        if (!window.appState.chatHistory) {
            try {
                window.appState.chatHistory = JSON.parse(localStorage.getItem('jobpilot_chat_history') || '[]');
            } catch (e) {
                window.appState.chatHistory = [];
            }
        }

        function saveHistory() {
            try {
                localStorage.setItem('jobpilot_chat_history', JSON.stringify(window.appState.chatHistory));
            } catch (e) {}
        }

        function renderInitialGreeting() {
            const div = document.createElement('div');
            div.className = 'ai-greeting-box';
            div.style.cssText = 'display: flex; gap: 12px; align-items: flex-start;';
            div.innerHTML = `
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #3b82f620; border: 1px solid #3b82f640; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0;">🤖</div>
                <div style="background: #0c101a; border: 1px solid #232d42; border-radius: 10px; padding: 14px 18px; max-width: 85%; color: #e2e8f0; font-size: 13px; line-height: 1.5;">
                    <p style="margin: 0 0 6px 0; font-weight: 600; color: #fff;">Hello! I am your JobPilot AI Agent. What would you like to configure or apply to today?</p>
                    <p style="margin: 0 0 10px 0; font-size: 12px; color: #94a3b8;">Click a quick task or type your custom instruction below:</p>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                        <button class="ai-chip" data-prompt="Change my target location to London and Remote, and add AI Engineer to my roles" style="background: #141a29; border: 1px solid #10b981; color: #34d399; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">⚙️ Set Target Location & Add Roles</button>
                        <button class="ai-chip" data-prompt="Set mode to Fresher (0-1 Yrs) and include remote opportunities" style="background: #141a29; border: 1px solid #3b82f6; color: #60a5fa; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">🎓 Switch to Fresher Mode</button>
                        <button class="ai-chip" data-prompt="Apply to 5 Python Developer jobs on LinkedIn in headless mode" style="background: #141a29; border: 1px solid #232d42; color: #60a5fa; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">🚀 Auto-Apply on LinkedIn</button>
                        <button class="ai-chip" data-prompt="Scan my Gmail inbox for recruiter interview invites and updates" style="background: #141a29; border: 1px solid #232d42; color: #34d399; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">📩 Scan Gmail for Interview Updates</button>
                        <button class="ai-chip" data-prompt="Write a tailored cover letter for Google for Software Engineer role" style="background: #141a29; border: 1px solid #232d42; color: #fbbf24; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">📝 Generate Cover Letter</button>
                    </div>
                </div>
            `;
            stream.appendChild(div);
            bindChips();
        }

        function triggerSettingsPrompt() {
            isSettingsMode = true;
            if (modeIndicator) modeIndicator.style.display = 'flex';
            if (input) {
                input.placeholder = "⚙️ Settings Mode: Tell AI what to change (e.g. 'Set target location to New York & Remote and add React Dev')...";
                input.focus();
            }

            const div = document.createElement('div');
            div.style.cssText = 'display: flex; gap: 12px; align-items: flex-start; animation: slideUp 0.25s ease-out;';
            div.innerHTML = `
                <div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(245, 158, 11, 0.2); border: 1px solid #f59e0b60; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0;">⚙️</div>
                <div style="background: #0c101a; border: 1px solid #f59e0b50; border-radius: 10px; padding: 14px 18px; max-width: 85%; color: #e2e8f0; font-size: 13px; line-height: 1.5; box-shadow: 0 4px 14px rgba(0,0,0,0.3);">
                    <div style="font-weight: 700; color: #fbbf24; font-size: 14px; margin-bottom: 4px;">⚙️ AI Settings Assistant: What would you like to update?</div>
                    <p style="font-size: 12px; color: #cbd5e1; margin: 0 0 10px 0;">
                        Tell me what configuration or preference you want to modify, or click any option below:
                    </p>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                        <button class="ai-chip" data-prompt="Change my target location to London and Bengaluru, and include remote opportunities" style="background: #141a29; border: 1px solid #10b981; color: #34d399; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">📍 Update Locations</button>
                        <button class="ai-chip" data-prompt="Add Full Stack Developer, AI Engineer, and Python Developer to my target roles" style="background: #141a29; border: 1px solid #3b82f6; color: #60a5fa; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">🎯 Update Target Roles</button>
                        <button class="ai-chip" data-prompt="Set mode to Fresher (0-1 Yrs)" style="background: #141a29; border: 1px solid #8b5cf6; color: #c4b5fd; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">🎓 Switch to Fresher</button>
                        <button class="ai-chip" data-prompt="Set mode to Experienced (1-3 Yrs)" style="background: #141a29; border: 1px solid #8b5cf6; color: #c4b5fd; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">💼 Switch to Experienced</button>
                        <button class="ai-chip" data-prompt="Set bot max applications per run to 15 and delay to 3000ms" style="background: #141a29; border: 1px solid #f59e0b; color: #fbbf24; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">⚡ Adjust Bot Limits & Delay</button>
                    </div>
                </div>
            `;
            stream.appendChild(div);
            stream.scrollTop = stream.scrollHeight;
            bindChips();
        }

        function cancelSettingsMode() {
            isSettingsMode = false;
            if (modeIndicator) modeIndicator.style.display = 'none';
            if (input) {
                input.placeholder = "Give instruction to AI (e.g. 'Change my location to London and add React Developer', 'Apply to 5 jobs on LinkedIn')...";
            }
        }

        function renderAllSavedMessages() {
            if (!stream) return;
            stream.innerHTML = '';
            renderInitialGreeting();

            const history = window.appState.chatHistory || [];
            history.forEach(item => {
                if (item.role === 'user') {
                    appendUserMessageUI(item.text, false);
                } else if (item.role === 'assistant') {
                    appendAiCardUI(item.data, false);
                }
            });

            stream.scrollTop = stream.scrollHeight;
        }

        function bindChips() {
            document.querySelectorAll('.ai-chip').forEach(chip => {
                chip.onclick = () => {
                    const p = chip.getAttribute('data-prompt');
                    if (p) {
                        input.value = p;
                        handleSend();
                    }
                };
            });
        }

        function appendUserMessageUI(text, save = true) {
            if (save) {
                window.appState.chatHistory.push({ role: 'user', text, timestamp: new Date().toISOString() });
                saveHistory();
            }

            const div = document.createElement('div');
            div.style.cssText = 'display: flex; gap: 10px; justify-content: flex-end; align-items: flex-start;';
            div.innerHTML = `
                <div style="background: #3b82f6; color: #fff; border-radius: 10px; padding: 10px 16px; max-width: 75%; font-size: 13px; line-height: 1.4; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                    ${text}
                </div>
                <div style="width: 30px; height: 30px; border-radius: 6px; background: #0c101a; border: 1px solid #232d42; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #fff; flex-shrink: 0;">YOU</div>
            `;
            stream.appendChild(div);
            stream.scrollTop = stream.scrollHeight;
        }

        function appendAiCardUI(response, save = true) {
            if (save) {
                window.appState.chatHistory.push({ role: 'assistant', data: response, timestamp: new Date().toISOString() });
                saveHistory();
            }

            const plan = response.plan || {};
            const exec = response.execution || {};
            const div = document.createElement('div');
            div.style.cssText = 'display: flex; gap: 10px; align-items: flex-start;';

            let actionBadge = `<span style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px; background: #3b82f620; color: #60a5fa; border: 1px solid #3b82f640;">Action: ${plan.action || 'Execute'}</span>`;
            
            let extraContent = '';
            if (exec.cover_letter) {
                extraContent = `
                    <div style="margin-top: 10px; background: #080c13; padding: 12px; border-radius: 6px; border: 1px solid #232d42; font-family: monospace; font-size: 12px; color: #cbd5e1; white-space: pre-wrap; max-height: 200px; overflow-y: auto;">${exec.cover_letter}</div>
                    <button class="btn btn-primary" onclick="navigator.clipboard.writeText(\`${exec.cover_letter.replace(/`/g, '\\`').replace(/\\/g, '\\\\')}\`); window.showToast('Cover letter copied!', 'success');" style="margin-top: 8px; padding: 5px 12px; font-size: 12px; border-radius: 6px;">📋 Copy Cover Letter</button>
                `;
            } else if (exec.config_updated) {
                extraContent = `
                    <div style="margin-top: 10px; background: #080c13; border: 1px solid #10b98140; padding: 12px 14px; border-radius: 8px;">
                        <div style="font-weight: 700; color: #34d399; font-size: 13px; margin-bottom: 6px;">⚙️ Configuration Updated Successfully</div>
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            ${(exec.changes || []).map(ch => `
                                <div style="font-size: 12px; color: #cbd5e1; display: flex; align-items: center; gap: 6px;">
                                    <span style="color: #10b981;">✓</span>
                                    <span>${ch}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else if (exec.stdout || exec.stderr) {
                extraContent = `
                    <div style="margin-top: 10px; background: #080c13; padding: 12px; border-radius: 6px; border: 1px solid #232d42;">
                        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px;">🖥️ Output:</div>
                        <pre style="margin: 0; font-family: monospace; font-size: 12px; color: #10b981; white-space: pre-wrap; max-height: 180px; overflow-y: auto;">${exec.stdout || exec.stderr}</pre>
                    </div>
                `;
            }

            div.innerHTML = `
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #3b82f620; border: 1px solid #3b82f640; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0;">🤖</div>
                <div style="background: #0c101a; border: 1px solid #232d42; border-radius: 10px; padding: 14px 18px; max-width: 85%; color: #e2e8f0; font-size: 13px; line-height: 1.5; box-shadow: 0 4px 14px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 700; color: #fff; font-size: 13px;">JobPilot AI Agent</span>
                        ${actionBadge}
                    </div>
                    ${plan.thought ? `<div style="font-size: 11px; color: #94a3b8; margin-bottom: 6px; padding: 5px 8px; background: #141a29; border-radius: 4px; border-left: 3px solid #3b82f6;">🧠 <em>${plan.thought}</em></div>` : ''}
                    <div style="font-size: 13px; color: #f1f5f9;">${plan.message_to_user || exec.message || 'Instruction executed.'}</div>
                    ${extraContent}
                </div>
            `;
            stream.appendChild(div);
            stream.scrollTop = stream.scrollHeight;
        }

        async function handleSend() {
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            cancelSettingsMode();
            appendUserMessageUI(text, true);

            const thinkingDiv = document.createElement('div');
            thinkingDiv.id = 'ai-thinking-indicator';
            thinkingDiv.style.cssText = 'display: flex; gap: 10px; align-items: center;';
            thinkingDiv.innerHTML = `
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #3b82f620; display: flex; align-items: center; justify-content: center; font-size: 16px;">🤖</div>
                <div style="background: #0c101a; border: 1px solid #232d42; border-radius: 10px; padding: 10px 16px; color: #94a3b8; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                    <span class="spinner" style="width: 13px; height: 13px; display: inline-block; border: 2px solid #3b82f6; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></span>
                    <span>JobPilot is reasoning and executing your command...</span>
                </div>
            `;
            stream.appendChild(thinkingDiv);
            stream.scrollTop = stream.scrollHeight;

            if (window.electronAPI && window.electronAPI.executeAiPrompt) {
                try {
                    const res = await window.electronAPI.executeAiPrompt(text);
                    thinkingDiv.remove();
                    appendAiCardUI(res, true);
                } catch (e) {
                    thinkingDiv.remove();
                    appendAiCardUI({
                        plan: { action: 'Error', message_to_user: 'Error executing prompt: ' + e.message }
                    }, true);
                }
            } else {
                thinkingDiv.remove();
                appendAiCardUI({
                    plan: { action: 'Offline', message_to_user: 'Electron IPC bridge not connected.' }
                }, true);
            }
        }

        changeSettingsBtn?.addEventListener('click', triggerSettingsPrompt);
        cancelModeBtn?.addEventListener('click', cancelSettingsMode);
        sendBtn?.addEventListener('click', handleSend);
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleSend();
        });

        clearBtn?.addEventListener('click', () => {
            window.appState.chatHistory = [];
            saveHistory();
            renderAllSavedMessages();
            window.showToast('Chat history cleared', 'info');
        });

        renderAllSavedMessages();
    }
};
