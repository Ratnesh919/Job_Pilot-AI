window.SettingsPage = {
    render: () => {
        const config = window.appState.config || {};
        const candidate = config.candidate || {};
        const apiKeys = config.api_keys || {};
        const email = config.email || {};
        const browser = config.browser || {};
        const botSettings = config.bot_settings || {};
        const roles = config.target_roles || [];

        return `
            <div class="settings-page" style="display: flex; flex-direction: column; gap: 24px; max-width: 860px; margin: 0 auto; padding-bottom: 60px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h2 style="margin: 0 0 4px 0; font-size: 22px; font-weight: 700; color: #fff;">⚙️ Configuration & Settings</h2>
                        <p style="margin: 0; font-size: 13px; color: #94a3b8;">Manage API keys, email dispatcher, Chrome browser session, and notification alerts.</p>
                    </div>
                    <button id="save-settings-btn-top" class="btn btn-primary" style="padding: 10px 22px; font-size: 14px; font-weight: 600; border-radius: 8px;">Save Changes</button>
                </div>
                
                <!-- 1. AI API Keys -->
                <div class="settings-section" style="background: #1a1f2e; padding: 22px 26px; border-radius: 12px; border: 1px solid #2a3142;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #2a3142; padding-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                        <span>🔑 Low-Latency LLM API Keys</span>
                        <span style="font-size: 11px; font-weight: 500; color: #10b981; background: #10b98115; padding: 2px 8px; border-radius: 10px;">Llama-3.3-70B Ready</span>
                    </h3>
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">OpenRouter API Key (sk-or-v1-...)</label>
                            <input type="text" id="set-openrouter" value="${apiKeys.openrouter || ''}" placeholder="sk-or-v1-..." style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; font-family: monospace; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">NVIDIA NIM API Key (nvapi-...)</label>
                            <input type="text" id="set-nvidia" value="${apiKeys.nvidia || ''}" placeholder="nvapi-..." style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; font-family: monospace; box-sizing: border-box;">
                        </div>
                    </div>
                </div>

                <!-- 2. Email & Status Scanner Config -->
                <div class="settings-section" style="background: #1a1f2e; padding: 22px 26px; border-radius: 12px; border: 1px solid #2a3142;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #2a3142; padding-bottom: 10px;">📧 Gmail Dispatcher & IMAP Status Scanner</h3>
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Sender Gmail Address</label>
                            <input type="email" id="set-email" value="${email.sender || 'kumarsinghratnesh3@gmail.com'}" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Google App Password (16 characters)</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="password" id="set-app-pass" value="${email.app_password || 'wgwzylnuiidwkosh'}" style="flex-grow: 1; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; font-family: monospace; box-sizing: border-box;">
                                <button id="test-smtp-btn" style="background: #2a3142; color: #3b82f6; border: 1px solid #3b82f6; padding: 0 18px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px;">Test SMTP</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 3. Candidate Profile -->
                <div class="settings-section" style="background: #1a1f2e; padding: 22px 26px; border-radius: 12px; border: 1px solid #2a3142;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #2a3142; padding-bottom: 10px;">👤 Candidate Profile & Portfolios</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Full Name</label>
                            <input type="text" id="set-name" value="${candidate.name || 'Ratnesh Kumar Singh'}" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Phone Number</label>
                            <input type="text" id="set-phone" value="${candidate.phone || '+91 70049 37129'}" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Location</label>
                            <input type="text" id="set-location" value="${candidate.location || 'Kolkata, West Bengal, India'}" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">LinkedIn URL</label>
                            <input type="text" id="set-linkedin" value="${candidate.linkedin || 'https://tinyurl.com/2st86aht'}" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Live Portfolio URL</label>
                            <input type="text" id="set-portfolio" value="${candidate.portfolio || 'https://my-portfolio-omega-liart-40.vercel.app'}" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Target Experience Level (For Job Filters)</label>
                            <select id="set-exp-level" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #3b82f6; color: #60a5fa; border-radius: 6px; font-size: 13px; font-weight: 600; box-sizing: border-box; outline: none;">
                                <option value="fresher" ${(config.experience_level || 'fresher') === 'fresher' ? 'selected' : ''}>🎓 Fresher / Entry-Level (0-1 Yrs) — Active</option>
                                <option value="experienced" ${(config.experience_level || '') === 'experienced' ? 'selected' : ''}>💼 Experienced (1-3 Yrs)</option>
                                <option value="senior" ${(config.experience_level || '') === 'senior' ? 'selected' : ''}>🚀 Senior / Lead (3+ Yrs)</option>
                            </select>
                            <span style="font-size: 11px; color: #94a3b8; margin-top: 3px; display: block;">When set to Fresher, the bot exclusively searches 0-1 Yr, Entry-Level, and 2026 Batch listings.</span>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Figma Prototypes URL</label>
                            <input type="text" id="set-figma" value="${candidate.figma || 'https://tinyurl.com/2c5nksav'}" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                    </div>
                </div>

                <!-- 4. Location Preferences -->
                <div class="settings-section" style="background: #1a1f2e; padding: 22px 26px; border-radius: 12px; border: 1px solid #2a3142;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #2a3142; padding-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                        <span>📍 Target Locations & City Preferences</span>
                    </h3>
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Primary Target Location (City / Region)</label>
                            <input type="text" id="set-primary-location" value="${config.primary_location || 'Kolkata, West Bengal, India'}" placeholder="e.g. Kolkata, Bengaluru, Hyderabad" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #10b981; color: #34d399; font-weight: 600; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Preferred Job Search Cities (Comma-separated)</label>
                            <input type="text" id="set-preferred-locations" value="${(config.preferred_locations || ['Kolkata', 'Bengaluru', 'Hyderabad', 'Pune', 'Remote']).join(', ')}" placeholder="Kolkata, Bengaluru, Hyderabad, Remote" style="width: 100%; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                            <span style="font-size: 11px; color: #94a3b8; margin-top: 3px; display: block;">The bot searches for jobs within and near these locations across LinkedIn, Indeed, Naukri, and company portals.</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; background: #0f1419; padding: 12px 16px; border-radius: 8px; border: 1px solid #2a3142;">
                            <div>
                                <div style="font-weight: 600; color: #fff; font-size: 13px;">Include Remote Opportunities</div>
                                <div style="font-size: 11px; color: #94a3b8;">Also search and apply to Remote & Work-From-Home roles worldwide.</div>
                            </div>
                            <input type="checkbox" id="set-include-remote" ${config.include_remote !== false ? 'checked' : ''} style="width: 18px; height: 18px; cursor: pointer; accent-color: #10b981;">
                        </div>
                    </div>
                </div>

                <!-- 4. Resume Document Section -->
                <div class="settings-section" style="background: #1a1f2e; padding: 22px 26px; border-radius: 12px; border: 1px solid #2a3142;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #2a3142; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <span>📄 Active Resume Document (PDF)</span>
                        <span style="font-size: 11px; color: #10b981; background: #10b98120; padding: 3px 8px; border-radius: 4px;">Attached to Form Submissions & Emails</span>
                    </h3>
                    <div style="display: flex; align-items: center; justify-content: space-between; background: #0f1419; border: 1px dashed #3b82f6; padding: 16px 20px; border-radius: 8px; gap: 14px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="font-size: 28px;">📄</div>
                            <div>
                                <div id="resume-filename-display" style="font-weight: 600; color: #fff; font-size: 14px;">${config.resume_path ? config.resume_path.split('\\\\').pop().split('/').pop() : 'Resume.pdf'}</div>
                                <div id="resume-path-display" style="font-size: 11px; color: #94a3b8; font-family: monospace; margin-top: 2px;">${config.resume_path || 'Resume.pdf (Active)'}</div>
                            </div>
                        </div>
                        <button type="button" id="btn-upload-resume" class="btn btn-primary" style="padding: 9px 18px; font-size: 13px; white-space: nowrap; display: flex; align-items: center; gap: 6px;">
                            <span>📁 Upload / Change Resume</span>
                        </button>
                    </div>
                </div>

                <!-- 5. Notifications & Browser Settings -->
                <div class="settings-section" style="background: #1a1f2e; padding: 22px 26px; border-radius: 12px; border: 1px solid #2a3142;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #2a3142; padding-bottom: 10px;">🔔 Alerts & Browser Engine</h3>
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; background: #0f1419; padding: 14px 18px; border-radius: 8px; border: 1px solid #2a3142;">
                            <div>
                                <div style="font-weight: 600; color: #fff; font-size: 14px;">Windows Native Desktop Notifications</div>
                                <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Receive desktop toast alerts when applications are submitted or recruiter updates arrive.</div>
                            </div>
                            <input type="checkbox" id="set-desktop-notifs" ${botSettings.enable_desktop_notifications !== false ? 'checked' : ''} style="width: 18px; height: 18px; cursor: pointer; accent-color: #3b82f6;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Google Chrome Automation Profile</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="text" id="set-chrome-data" value="${browser.user_data_path || 'C:\\Users\\akssi\\AppData\\Local\\Google\\Chrome\\User Data'}" style="flex-grow: 1; padding: 10px 14px; background: #0f1419; border: 1px solid #2a3142; color: white; border-radius: 6px; font-size: 13px; font-family: monospace; box-sizing: border-box;">
                                <button id="open-login-browser-btn" style="background: #2a3142; color: #10b981; border: 1px solid #10b981; padding: 0 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; white-space: nowrap;">🌐 Login to Portals</button>
                            </div>
                            <span style="font-size: 11px; color: #94a3b8; margin-top: 4px; display: block;">Click 'Login to Portals' to open a browser window and log into LinkedIn & Naukri once.</span>
                        </div>
                    </div>
                </div>

                <div style="display: flex; justify-content: flex-end;">
                    <button id="save-settings-btn" class="btn btn-primary" style="padding: 12px 28px; font-size: 15px; font-weight: 700; border-radius: 8px;">Save Settings</button>
                </div>
            </div>
        `;
    },

    init: () => {
        const testBtn = document.getElementById('test-smtp-btn');
        const loginBrowserBtn = document.getElementById('open-login-browser-btn');
        const uploadResumeBtn = document.getElementById('btn-upload-resume');
        const saveBtns = [document.getElementById('save-settings-btn'), document.getElementById('save-settings-btn-top')];

        uploadResumeBtn?.addEventListener('click', async () => {
            if (window.electronAPI && window.electronAPI.selectResumeFile) {
                const res = await window.electronAPI.selectResumeFile();
                if (res.success) {
                    const fnEl = document.getElementById('resume-filename-display');
                    const fpEl = document.getElementById('resume-path-display');
                    if (fnEl) fnEl.textContent = res.fileName;
                    if (fpEl) fpEl.textContent = res.filePath;
                    window.showToast(`Resume uploaded successfully: ${res.fileName}`, 'success');
                }
            }
        });

        loginBrowserBtn?.addEventListener('click', async () => {
            if (window.electronAPI && window.electronAPI.openLoginBrowser) {
                window.showToast('Opening Chrome window. Log in to LinkedIn and Naukri...', 'info');
                await window.electronAPI.openLoginBrowser();
            }
        });

        testBtn?.addEventListener('click', async () => {
            testBtn.disabled = true;
            testBtn.textContent = 'Testing...';
            if (window.electronAPI && window.electronAPI.testSmtp) {
                const ok = await window.electronAPI.testSmtp();
                if (ok) {
                    window.showToast('Gmail SMTP Authentication Verified! Ready to send applications.', 'success');
                } else {
                    window.showToast('SMTP Test Failed. Check Gmail address or App Password.', 'error');
                }
            }
            testBtn.disabled = false;
            testBtn.textContent = 'Test SMTP';
        });

        const saveHandler = async () => {
            const current = window.appState.config || {};
            const updated = {
                ...current,
                candidate: {
                    ...current.candidate,
                    name: document.getElementById('set-name')?.value || '',
                    phone: document.getElementById('set-phone')?.value || '',
                    location: document.getElementById('set-location')?.value || '',
                    linkedin: document.getElementById('set-linkedin')?.value || '',
                    portfolio: document.getElementById('set-portfolio')?.value || '',
                    figma: document.getElementById('set-figma')?.value || ''
                },
                api_keys: {
                    ...current.api_keys,
                    openrouter: document.getElementById('set-openrouter')?.value || '',
                    nvidia: document.getElementById('set-nvidia')?.value || ''
                },
                email: {
                    ...current.email,
                    sender: document.getElementById('set-email')?.value || '',
                    app_password: document.getElementById('set-app-pass')?.value || ''
                },
                browser: {
                    ...current.browser,
                    user_data_path: document.getElementById('set-chrome-data')?.value || ''
                },
                bot_settings: {
                    ...current.bot_settings,
                    enable_desktop_notifications: document.getElementById('set-desktop-notifs')?.checked
                },
                experience_level: document.getElementById('set-exp-level')?.value || 'fresher',
                primary_location: document.getElementById('set-primary-location')?.value || 'Kolkata',
                preferred_locations: (document.getElementById('set-preferred-locations')?.value || 'Kolkata, Bengaluru, Remote').split(',').map(s => s.trim()).filter(Boolean),
                include_remote: document.getElementById('set-include-remote')?.checked !== false
            };

            if (window.electronAPI && window.electronAPI.saveConfig) {
                const ok = await window.electronAPI.saveConfig(updated);
                if (ok) {
                    window.appState.config = updated;
                    window.showToast('Settings saved and persisted successfully!', 'success');
                } else {
                    window.showToast('Failed to save settings.', 'error');
                }
            }
        };

        saveBtns.forEach(btn => btn?.addEventListener('click', saveHandler));
    }
};
