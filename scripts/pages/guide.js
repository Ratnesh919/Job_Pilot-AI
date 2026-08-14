window.GuidePage = {
    render: () => {
        return `
            <div class="guide-page" style="display: flex; flex-direction: column; gap: 22px; max-width: 1000px; margin: 0 auto;">
                <!-- Header Banner -->
                <div style="background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.15)); border: 1px solid #3b82f640; border-radius: 12px; padding: 22px 26px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 28px;">📖</span>
                        <div>
                            <h2 style="margin: 0; font-size: 18px; font-weight: 700; color: #fff;">JobPilot-AI Setup & Free API Keys Guide</h2>
                            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">Everything you need to configure your free AI keys, Gmail SMTP, and start auto-applying to jobs.</p>
                        </div>
                    </div>
                </div>

                <!-- Important Prerequisite Alert -->
                <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid #f59e0b50; border-radius: 12px; padding: 20px 24px; display: flex; gap: 14px; align-items: flex-start;">
                    <span style="font-size: 26px; line-height: 1;">⚠️</span>
                    <div style="flex-grow: 1;">
                        <div style="font-weight: 700; color: #fbbf24; font-size: 14px; margin-bottom: 4px;">IMPORTANT PREREQUISITE: Log into your Chrome accounts ONCE</div>
                        <p style="font-size: 12px; color: #cbd5e1; line-height: 1.5; margin: 0 0 10px 0;">
                            For automated job applications on <strong>LinkedIn</strong>, <strong>Naukri</strong>, and <strong>Indeed</strong> to work smoothly without triggering CAPTCHAs, JobPilot-AI connects securely to your local Google Chrome session. You only need to log in <strong>once</strong>.
                        </p>
                        <button class="btn btn-primary" id="guide-open-login-btn" style="font-size: 12px; padding: 7px 16px; display: inline-flex; align-items: center; gap: 6px;">
                            <span>🌐 Open Chrome to Log In (1-Click)</span>
                        </button>
                    </div>
                </div>

                <!-- 1. Free API Keys Section -->
                <div class="guide-section" style="background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 22px 26px;">
                    <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
                        <span>🔑 How to Get 100% FREE AI API Keys</span>
                    </h3>
                    <p style="font-size: 13px; color: #94a3b8; line-height: 1.5; margin-bottom: 18px;">
                        JobPilot-AI supports free-tier LLM models like <strong>Meta Llama 3.3 70B</strong> and <strong>Google Gemini Flash</strong> for zero-cost cover letter generation and command reasoning.
                    </p>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <!-- OpenRouter Box -->
                        <div style="background: #0c101a; border: 1px solid #232d42; border-radius: 10px; padding: 16px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-weight: 700; color: #60a5fa; font-size: 14px;">1. OpenRouter (Recommended)</span>
                                <span style="background: #10b98120; color: #34d399; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;">Free Models</span>
                            </div>
                            <p style="font-size: 12px; color: #94a3b8; line-height: 1.4; margin-bottom: 12px;">
                                Provides free access to Llama-3.3-70B, DeepSeek-R1, and Mistral.
                            </p>
                            <ol style="font-size: 12px; color: #cbd5e1; padding-left: 18px; line-height: 1.6; margin-bottom: 14px;">
                                <li>Visit <a href="#" class="guide-ext-link" data-url="https://openrouter.ai/keys" style="color: #60a5fa; text-decoration: underline;">openrouter.ai/keys</a></li>
                                <li>Sign in with Google or GitHub.</li>
                                <li>Click <strong>Create Key</strong> and copy the <code>sk-or-v1-...</code> string.</li>
                                <li>Paste it into the <strong>Settings</strong> tab.</li>
                            </ol>
                            <button class="btn btn-secondary guide-open-url" data-url="https://openrouter.ai/keys" style="width: 100%; font-size: 12px; padding: 8px;">Get Free OpenRouter Key ↗</button>
                        </div>

                        <!-- NVIDIA NIM Box -->
                        <div style="background: #0c101a; border: 1px solid #232d42; border-radius: 10px; padding: 16px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-weight: 700; color: #34d399; font-size: 14px;">2. NVIDIA NIM Cloud</span>
                                <span style="background: #3b82f620; color: #60a5fa; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;">1000 Free Credits</span>
                            </div>
                            <p style="font-size: 12px; color: #94a3b8; line-height: 1.4; margin-bottom: 12px;">
                                Enterprise-grade high-speed API keys directly from NVIDIA.
                            </p>
                            <ol style="font-size: 12px; color: #cbd5e1; padding-left: 18px; line-height: 1.6; margin-bottom: 14px;">
                                <li>Visit <a href="#" class="guide-ext-link" data-url="https://build.nvidia.com" style="color: #34d399; text-decoration: underline;">build.nvidia.com</a></li>
                                <li>Sign up for a free developer account.</li>
                                <li>Generate your <code>nvapi-...</code> key.</li>
                                <li>Paste it into the <strong>Settings</strong> tab.</li>
                            </ol>
                            <button class="btn btn-secondary guide-open-url" data-url="https://build.nvidia.com" style="width: 100%; font-size: 12px; padding: 8px;">Get Free NVIDIA Key ↗</button>
                        </div>
                    </div>
                </div>

                <!-- 2. Gmail SMTP Setup -->
                <div class="guide-section" style="background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 22px 26px;">
                    <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
                        <span>✉️ How to Generate a Gmail App Password (SMTP)</span>
                    </h3>
                    <p style="font-size: 13px; color: #94a3b8; line-height: 1.5; margin-bottom: 14px;">
                        To allow JobPilot-AI to email your PDF resume directly to recruiters and scan your inbox for interview updates:
                    </p>

                    <div style="background: #0c101a; border: 1px solid #232d42; border-radius: 8px; padding: 16px;">
                        <ol style="font-size: 13px; color: #cbd5e1; padding-left: 20px; line-height: 1.8;">
                            <li>Ensure <strong>2-Step Verification</strong> is ON in your <a href="#" class="guide-ext-link" data-url="https://myaccount.google.com/security" style="color: #60a5fa; text-decoration: underline;">Google Security Settings</a>.</li>
                            <li>Go directly to <a href="#" class="guide-ext-link" data-url="https://myaccount.google.com/apppasswords" style="color: #60a5fa; text-decoration: underline;">myaccount.google.com/apppasswords</a>.</li>
                            <li>Enter an App Name (e.g. <code>JobPilot</code>) and click <strong>Create</strong>.</li>
                            <li>Copy the <strong>16-letter password</strong> (e.g., <code>abcd efgh ijkl mnop</code>).</li>
                            <li>Paste your Gmail and this 16-letter key in <strong>Settings</strong> -> click <strong>Test SMTP Connection</strong>!</li>
                        </ol>
                        <div style="margin-top: 14px; display: flex; gap: 10px;">
                            <button class="btn btn-primary guide-open-url" data-url="https://myaccount.google.com/apppasswords" style="font-size: 12px; padding: 8px 16px;">Open Google App Passwords ↗</button>
                        </div>
                    </div>
                </div>

                <!-- 3. AI Command Bar Examples -->
                <div class="guide-section" style="background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 22px 26px;">
                    <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
                        <span>🧠 Natural Language AI Commands You Can Use</span>
                    </h3>
                    <p style="font-size: 13px; color: #94a3b8; line-height: 1.5; margin-bottom: 14px;">
                        You can control every aspect of JobPilot-AI using the topbar prompt or AI Command Agent:
                    </p>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div style="background: #0c101a; padding: 12px 14px; border-radius: 8px; border: 1px solid #232d42;">
                            <div style="font-weight: 600; color: #60a5fa; font-size: 13px;">📍 Change Target Locations</div>
                            <div style="font-size: 12px; color: #94a3b8; font-family: monospace; margin-top: 4px;">"Change my target location to Bengaluru and Pune and include remote"</div>
                        </div>
                        <div style="background: #0c101a; padding: 12px 14px; border-radius: 8px; border: 1px solid #232d42;">
                            <div style="font-weight: 600; color: #34d399; font-size: 13px;">🎯 Update Target Roles</div>
                            <div style="font-size: 12px; color: #94a3b8; font-family: monospace; margin-top: 4px;">"Add React Developer and Golang Engineer to my target roles"</div>
                        </div>
                        <div style="background: #0c101a; padding: 12px 14px; border-radius: 8px; border: 1px solid #232d42;">
                            <div style="font-weight: 600; color: #fbbf24; font-size: 13px;">🎓 Switch Experience Mode</div>
                            <div style="font-size: 12px; color: #94a3b8; font-family: monospace; margin-top: 4px;">"Set mode to Fresher (0-1 Yrs)" or "Switch to Experienced 2 Yrs"</div>
                        </div>
                        <div style="background: #0c101a; padding: 12px 14px; border-radius: 8px; border: 1px solid #232d42;">
                            <div style="font-weight: 600; color: #a78bfa; font-size: 13px;">📩 Scan Interview Invites</div>
                            <div style="font-size: 12px; color: #94a3b8; font-family: monospace; margin-top: 4px;">"Scan my Gmail inbox for recruiter interview invites and tests"</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init: () => {
        document.getElementById('guide-open-login-btn')?.addEventListener('click', async () => {
            if (window.electronAPI && window.electronAPI.openLoginBrowser) {
                window.showToast('Opening Chrome. Log in to LinkedIn, Naukri, and Indeed.', 'info');
                await window.electronAPI.openLoginBrowser();
            }
        });

        document.querySelectorAll('.guide-open-url, .guide-ext-link').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                const url = el.getAttribute('data-url');
                if (url && window.electronAPI && window.electronAPI.openExternal) {
                    window.electronAPI.openExternal(url);
                }
            });
        });
    }
};
