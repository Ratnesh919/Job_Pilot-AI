window.SettingsPage = {
    render: () => {
        const config = window.appState.config || {};
        const candidate = config.candidate || {};
        const apiKeys = config.api_keys || {};
        const email = config.email || {};
        const browser = config.browser || {};
        const botSettings = config.bot_settings || {};

        return `
            <div class="settings-page" style="display: flex; flex-direction: column; gap: 20px; max-width: 900px; margin: 0 auto;">
                
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h2 style="margin: 0; font-size: 18px; color: #fff; font-weight: 700;">System Settings & Configuration</h2>
                        <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">Manage your candidate profile, target locations, API credentials, and email automation.</p>
                    </div>
                    <button id="save-settings-btn-top" class="btn btn-primary" style="padding: 9px 20px; font-size: 13px;">Save Changes</button>
                </div>

                <!-- 1. AI API Credentials -->
                <div class="settings-section" style="background: #141a29; padding: 22px 26px; border-radius: 12px; border: 1px solid #232d42;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #232d42; padding-bottom: 10px; margin-bottom: 16px;">
                        <h3 style="margin: 0; font-size: 15px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
                            <span>🔑 LLM API Keys (Free Tier Supported)</span>
                        </h3>
                        <a href="#guide" style="font-size: 12px; color: #3b82f6; text-decoration: underline;">How to get free keys ↗</a>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                <label style="font-size: 13px; color: #cbd5e1; font-weight: 500;">OpenRouter API Key (Llama 3.3 70B & Free Models)</label>
                                <span class="guide-ext-link" data-url="https://openrouter.ai/keys" style="font-size: 11px; color: #60a5fa; cursor: pointer;">openrouter.ai/keys ↗</span>
                            </div>
                            <input type="password" id="set-openrouter" value="${apiKeys.openrouter || ''}" placeholder="sk-or-v1-..." style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; font-family: monospace; box-sizing: border-box;">
                        </div>

                        <div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                <label style="font-size: 13px; color: #cbd5e1; font-weight: 500;">NVIDIA NIM API Key</label>
                                <span class="guide-ext-link" data-url="https://build.nvidia.com" style="font-size: 11px; color: #34d399; cursor: pointer;">build.nvidia.com ↗</span>
                            </div>
                            <input type="password" id="set-nvidia" value="${apiKeys.nvidia || ''}" placeholder="nvapi-..." style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; font-family: monospace; box-sizing: border-box;">
                        </div>
                    </div>
                </div>

                <!-- 2. Gmail SMTP & Dispatch Settings -->
                <div class="settings-section" style="background: #141a29; padding: 22px 26px; border-radius: 12px; border: 1px solid #232d42;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #232d42; padding-bottom: 10px; margin-bottom: 16px;">
                        <h3 style="margin: 0; font-size: 15px; font-weight: 700; color: #fff;">✉️ Gmail SMTP & Application Dispatch</h3>
                        <a href="#guide" style="font-size: 12px; color: #3b82f6; text-decoration: underline;">App password tutorial ↗</a>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Your Gmail Address</label>
                            <input type="email" id="set-email" value="${email.sender || ''}" placeholder="your_email@gmail.com" style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">16-Letter Gmail App Password</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="password" id="set-app-pass" value="${email.app_password || ''}" placeholder="abcd efgh ijkl mnop" style="flex-grow: 1; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; font-family: monospace; box-sizing: border-box;">
                                <button id="test-smtp-btn" class="btn btn-secondary" style="font-size: 12px; padding: 0 14px; white-space: nowrap;">Test SMTP</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 3. Location Preferences -->
                <div class="settings-section" style="background: #141a29; padding: 22px 26px; border-radius: 12px; border: 1px solid #232d42;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #232d42; padding-bottom: 10px;">📍 Target Locations & Relocation Preferences</h3>
                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Primary Target City / Region</label>
                            <input type="text" id="set-primary-location" value="${config.primary_location || 'Remote'}" placeholder="e.g. Remote, New York, Bengaluru" style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #10b981; color: #34d399; font-weight: 600; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Preferred Job Search Cities (Comma-separated)</label>
                            <input type="text" id="set-preferred-locations" value="${(config.preferred_locations || ['Remote', 'New York', 'London']).join(', ')}" placeholder="Remote, New York, Bengaluru, London" style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; background: #0c101a; padding: 12px 16px; border-radius: 8px; border: 1px solid #232d42;">
                            <div>
                                <div style="font-weight: 600; color: #fff; font-size: 13px;">Include Remote Opportunities</div>
                                <div style="font-size: 11px; color: #94a3b8;">Also search and apply to Remote / Work-From-Home roles worldwide.</div>
                            </div>
                            <input type="checkbox" id="set-include-remote" ${config.include_remote !== false ? 'checked' : ''} style="width: 18px; height: 18px; cursor: pointer; accent-color: #10b981;">
                        </div>
                    </div>
                </div>

                <!-- 4. Resume Document Section -->
                <div class="settings-section" style="background: #141a29; padding: 22px 26px; border-radius: 12px; border: 1px solid #232d42;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #232d42; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <span>📄 Active Resume Document (PDF)</span>
                        <span style="font-size: 11px; color: #10b981; background: #10b98120; padding: 3px 8px; border-radius: 4px;">Attached to Form Submissions & Emails</span>
                    </h3>
                    <div style="display: flex; align-items: center; justify-content: space-between; background: #0c101a; border: 1px dashed #3b82f6; padding: 16px 20px; border-radius: 8px; gap: 14px;">
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

                <!-- 5. Candidate Profile -->
                <div class="settings-section" style="background: #141a29; padding: 22px 26px; border-radius: 12px; border: 1px solid #232d42;">
                    <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #fff; border-bottom: 1px solid #232d42; padding-bottom: 10px;">👤 Candidate Profile & Resume Links</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Full Name</label>
                            <input type="text" id="set-name" value="${candidate.name || ''}" placeholder="Your Full Name" style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Phone Number</label>
                            <input type="text" id="set-phone" value="${candidate.phone || ''}" placeholder="+1 (555) 000-0000" style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Target Experience Mode</label>
                            <select id="set-exp-level" style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #3b82f6; color: #60a5fa; border-radius: 6px; font-size: 13px; font-weight: 600; box-sizing: border-box; outline: none;">
                                <option value="fresher" ${(config.experience_level || 'fresher') === 'fresher' ? 'selected' : ''}>🎓 Fresher / Entry-Level (0-1 Yrs)</option>
                                <option value="experienced" ${(config.experience_level || '') === 'experienced' ? 'selected' : ''}>💼 Experienced (1-3 Yrs)</option>
                                <option value="senior" ${(config.experience_level || '') === 'senior' ? 'selected' : ''}>🚀 Senior / Lead (3+ Yrs)</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">LinkedIn URL</label>
                            <input type="text" id="set-linkedin" value="${candidate.linkedin || ''}" placeholder="https://linkedin.com/in/..." style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">Portfolio Website URL</label>
                            <input type="text" id="set-portfolio" value="${candidate.portfolio || ''}" placeholder="https://yourportfolio.dev" style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-size: 13px; color: #cbd5e1; font-weight: 500;">GitHub Profile URL</label>
                            <input type="text" id="set-github" value="${candidate.github || ''}" placeholder="https://github.com/..." style="width: 100%; padding: 10px 14px; background: #0c101a; border: 1px solid #232d42; color: white; border-radius: 6px; font-size: 13px; box-sizing: border-box;">
                        </div>
                    </div>
                </div>

                <div style="display: flex; justify-content: flex-end;">
                    <button id="save-settings-btn" class="btn btn-primary" style="padding: 12px 28px; font-size: 14px; font-weight: 700; border-radius: 8px;">Save Settings</button>
                </div>
            </div>
        `;
    },

    init: () => {
        const testBtn = document.getElementById('test-smtp-btn');
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

        document.querySelectorAll('.guide-ext-link').forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                const url = el.getAttribute('data-url');
                if (url && window.electronAPI && window.electronAPI.openExternal) {
                    window.electronAPI.openExternal(url);
                }
            });
        });

        testBtn?.addEventListener('click', async () => {
            testBtn.textContent = 'Testing...';
            testBtn.disabled = true;
            if (window.electronAPI && window.electronAPI.testSmtp) {
                const ok = await window.electronAPI.testSmtp();
                if (ok) {
                    window.showToast('SMTP Test Passed! Connected to Gmail.', 'success');
                } else {
                    window.showToast('SMTP Test Failed. Check Gmail address & App Password.', 'error');
                }
            }
            testBtn.textContent = 'Test SMTP';
            testBtn.disabled = false;
        });

        const saveHandler = async () => {
            const current = window.appState.config || {};
            const updated = {
                ...current,
                candidate: {
                    ...current.candidate,
                    name: document.getElementById('set-name')?.value || '',
                    phone: document.getElementById('set-phone')?.value || '',
                    linkedin: document.getElementById('set-linkedin')?.value || '',
                    portfolio: document.getElementById('set-portfolio')?.value || '',
                    github: document.getElementById('set-github')?.value || ''
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
                experience_level: document.getElementById('set-exp-level')?.value || 'fresher',
                primary_location: document.getElementById('set-primary-location')?.value || 'Remote',
                preferred_locations: (document.getElementById('set-preferred-locations')?.value || 'Remote, New York, London').split(',').map(s => s.trim()).filter(Boolean),
                include_remote: document.getElementById('set-include-remote')?.checked !== false
            };

            if (window.electronAPI && window.electronAPI.saveConfig) {
                const ok = await window.electronAPI.saveConfig(updated);
                if (ok) {
                    window.appState.config = updated;
                    window.showToast('Settings saved successfully!', 'success');
                } else {
                    window.showToast('Failed to save settings.', 'error');
                }
            }
        };

        saveBtns.forEach(btn => btn?.addEventListener('click', saveHandler));
    }
};
