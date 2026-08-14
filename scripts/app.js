// ─── JobPilot-AI Global Application Controller ───

window.appState = {
    config: {},
    stats: {},
    applications: [],
    botStatus: { running: false, startTime: null, appliedCount: 0 },
    chatHistory: []
};

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Toast Notification System
    window.showToast = (message, type = 'info') => {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'toast';
        
        let borderClr = '#3b82f6';
        let icon = 'ℹ️';
        if (type === 'success') { borderClr = '#10b981'; icon = '✅'; }
        else if (type === 'error') { borderClr = '#ef4444'; icon = '⚠️'; }

        toast.style.borderLeft = `4px solid ${borderClr}`;
        toast.innerHTML = `<span style="margin-right: 8px;">${icon}</span><span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    };

    window.formatTime = (seconds) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}m ${s}s`;
    };

    window.getStatusBadge = (status) => {
        let bg = 'rgba(59, 130, 246, 0.15)';
        let color = '#60a5fa';
        let icon = '•';

        if (status === 'Interview Scheduled' || (status && status.includes('Interview'))) {
            bg = 'rgba(16, 185, 129, 0.15)';
            color = '#34d399';
            icon = '🎉';
        } else if (status === 'Selected / Offered' || (status && status.includes('Offer'))) {
            bg = 'rgba(6, 182, 212, 0.15)';
            color = '#22d3ee';
            icon = '🏆';
        } else if (status === 'Under Review' || (status && status.includes('Review'))) {
            bg = 'rgba(245, 158, 11, 0.15)';
            color = '#fbbf24';
            icon = '⏳';
        } else if (status === 'Assessment / Test' || (status && status.includes('Test'))) {
            bg = 'rgba(139, 92, 246, 0.15)';
            color = '#a78bfa';
            icon = '📝';
        } else if (status === 'Rejected' || (status && status.includes('Reject'))) {
            bg = 'rgba(239, 68, 68, 0.15)';
            color = '#f87171';
            icon = '✕';
        }

        return `<span style="background: ${bg}; color: ${color}; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">${icon} ${status || 'Applied'}</span>`;
    };

    // 2. Navigation Router
    const routes = {
        '#dashboard': { page: window.DashboardPage, title: 'Dashboard', subtitle: 'Real-time overview of your autonomous job application bot' },
        '#ai-agent': { page: window.AiAgentPage, title: 'AI Command Agent', subtitle: 'Give instructions to search jobs, modify settings, or generate custom cover letters' },
        '#tracker': { page: window.TrackerPage, title: 'Application Tracker', subtitle: 'Manage, search, and update all dispatched job applications' },
        '#guide': { page: window.GuidePage, title: 'Setup Guide & Free Keys', subtitle: 'Step-by-step instructions for free API keys, Gmail SMTP, and usage' },
        '#settings': { page: window.SettingsPage, title: 'Settings', subtitle: 'Configure candidate profile, target locations, and automation settings' }
    };

    function navigate() {
        const hash = window.location.hash || '#dashboard';
        const route = routes[hash] || routes['#dashboard'];
        const container = document.getElementById('page-container');
        const titleEl = document.getElementById('page-title');
        const subEl = document.getElementById('page-subtitle');

        if (titleEl && subEl) {
            const candName = window.appState.config?.candidate?.name || 'Job Candidate';
            titleEl.textContent = hash === '#dashboard' ? `👋 Hi, ${candName}` : route.title;
            subEl.textContent = route.subtitle;
        }

        if (container && route.page) {
            container.innerHTML = route.page.render();
            if (route.page.init) route.page.init();

            document.querySelectorAll('.sidebar-nav a').forEach(el => {
                if (el.getAttribute('href') === hash) el.classList.add('active');
                else el.classList.remove('active');
            });
        }
    }

    window.addEventListener('hashchange', navigate);

    // 3. Application Details Modal
    window.openApplicationModal = (appData) => {
        const overlay = document.getElementById('app-modal-overlay');
        const companyEl = document.getElementById('modal-company');
        const roleEl = document.getElementById('modal-role');
        const statusBadgeEl = document.getElementById('modal-status-badge');
        const statusSelect = document.getElementById('modal-status-select');
        const historyList = document.getElementById('modal-history-list');
        const updateBtn = document.getElementById('modal-update-btn');
        const closeBtn = document.getElementById('modal-close-btn');

        if (!overlay) return;

        companyEl.textContent = appData.company || 'Company';
        roleEl.textContent = appData.role || 'Job Position';
        statusBadgeEl.innerHTML = window.getStatusBadge(appData.status || 'Applied');
        statusSelect.value = appData.status || 'Applied';

        const history = appData.history || [];
        if (history.length === 0) {
            historyList.innerHTML = `<div style="color: #94a3b8; font-size: 13px;">No timeline updates recorded.</div>`;
        } else {
            historyList.innerHTML = history.slice().reverse().map(h => `
                <div style="position: relative; padding-bottom: 12px; margin-left: 12px;">
                    <div style="position: absolute; left: -19px; top: 3px; width: 10px; height: 10px; border-radius: 50%; background: #3b82f6;"></div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; font-size: 13px; color: #fff;">${h.status}</span>
                        <span style="font-size: 11px; color: #64748b;">${h.date}</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">${h.note || 'Status updated'}</div>
                </div>
            `).join('');
        }

        overlay.style.display = 'flex';

        updateBtn.onclick = async () => {
            const newStatus = statusSelect.value;
            if (window.electronAPI && window.electronAPI.updateApplicationStatus) {
                await window.electronAPI.updateApplicationStatus({ id: appData.id, newStatus, note: 'Manually updated' });
                window.showToast(`Updated ${appData.company} to ${newStatus}`, 'success');
                overlay.style.display = 'none';
                if (window.electronAPI.getApplications) {
                    window.appState.applications = await window.electronAPI.getApplications();
                    navigate();
                }
            }
        };

        closeBtn.onclick = () => { overlay.style.display = 'none'; };
        overlay.onclick = (e) => { if (e.target === overlay) overlay.style.display = 'none'; };
    };

    // 4. Initial Load
    if (window.electronAPI) {
        if (window.electronAPI.getConfig) window.appState.config = await window.electronAPI.getConfig();
        if (window.electronAPI.getStats) window.appState.stats = await window.electronAPI.getStats();
        if (window.electronAPI.getApplications) window.appState.applications = await window.electronAPI.getApplications();
        if (window.electronAPI.getBotStatus) window.appState.botStatus = await window.electronAPI.getBotStatus();
    }

    // 5. Update Sidebar Candidate Info
    const userNameEl = document.getElementById('user-name');
    const userEmailEl = document.getElementById('user-email');
    const userAvatarEl = document.getElementById('user-avatar');
    if (userNameEl && window.appState.config?.candidate?.name) {
        userNameEl.textContent = window.appState.config.candidate.name;
        const initials = window.appState.config.candidate.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        if (userAvatarEl) userAvatarEl.textContent = initials || 'JP';
    }
    if (userEmailEl && window.appState.config?.candidate?.email) {
        userEmailEl.textContent = window.appState.config.candidate.email;
    }

    // 6. Bot Toggle Controls
    const botBtn = document.getElementById('bot-toggle-btn');
    const statusDot = document.getElementById('bot-status-dot');
    const statusText = document.getElementById('bot-status-text');
    const appliedEl = document.getElementById('bot-applied');
    const runtimeEl = document.getElementById('bot-runtime');

    function syncBotStatusUI(status) {
        if (status.running) {
            if (botBtn) {
                botBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Stop Bot</span>';
                botBtn.className = 'btn btn-danger bot-toggle-btn';
            }
            if (statusDot) statusDot.className = 'status-dot active';
            if (statusText) statusText.textContent = 'Active';
        } else {
            if (botBtn) {
                botBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>Start Bot</span>';
                botBtn.className = 'btn btn-primary bot-toggle-btn';
            }
            if (statusDot) statusDot.className = 'status-dot inactive';
            if (statusText) statusText.textContent = 'Idle';
            if (runtimeEl) runtimeEl.textContent = '0m 0s';
        }
        if (appliedEl) appliedEl.textContent = window.appState.applications.length || 0;
    }

    botBtn?.addEventListener('click', async () => {
        if (!window.electronAPI) return;
        if (window.appState.botStatus.running) {
            const res = await window.electronAPI.stopBot();
            window.showToast(res.message, res.success ? 'success' : 'error');
        } else {
            const res = await window.electronAPI.startBot({ headless: true });
            window.showToast(res.message, res.success ? 'success' : 'error');
        }
    });

    setInterval(async () => {
        if (window.electronAPI && window.electronAPI.getBotStatus) {
            const st = await window.electronAPI.getBotStatus();
            window.appState.botStatus = st;
            syncBotStatusUI(st);
            if (st.running && st.startTime && runtimeEl) {
                runtimeEl.textContent = window.formatTime(Math.floor((Date.now() - st.startTime) / 1000));
            }
        }
    }, 1000);

    // 7. Universal Prompt Bar
    const universalInput = document.getElementById('universal-ai-input');
    const universalBtn = document.getElementById('universal-ai-btn');

    function handleUniversalPrompt() {
        const text = universalInput?.value.trim();
        if (!text) return;
        universalInput.value = '';
        window.location.hash = '#ai-agent';
        setTimeout(() => {
            const pageInput = document.getElementById('ai-prompt-input');
            const sendBtn = document.getElementById('ai-send-btn');
            if (pageInput && sendBtn) {
                pageInput.value = text;
                sendBtn.click();
            }
        }, 150);
    }

    universalBtn?.addEventListener('click', handleUniversalPrompt);
    universalInput?.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleUniversalPrompt(); });

    // 8. Topbar Location & Experience Mode Selectors
    const locSelector = document.getElementById('global-loc-selector');
    const expSelector = document.getElementById('global-exp-selector');

    if (locSelector) {
        if (window.appState.config?.primary_location) {
            const p = window.appState.config.primary_location.toLowerCase();
            for (let opt of locSelector.options) {
                if (p.includes(opt.value.toLowerCase())) {
                    locSelector.value = opt.value;
                    break;
                }
            }
        }
        locSelector.addEventListener('change', async (e) => {
            const val = e.target.value;
            if (window.appState.config) {
                window.appState.config.primary_location = val;
                if (window.electronAPI && window.electronAPI.saveConfig) {
                    await window.electronAPI.saveConfig(window.appState.config);
                    window.showToast(`Target location set to: ${val}`, 'success');
                }
            }
        });
    }

    if (expSelector) {
        if (window.appState.config?.experience_level) {
            expSelector.value = window.appState.config.experience_level;
        }
        expSelector.addEventListener('change', async (e) => {
            const val = e.target.value;
            if (window.appState.config) {
                window.appState.config.experience_level = val;
                if (window.electronAPI && window.electronAPI.saveConfig) {
                    await window.electronAPI.saveConfig(window.appState.config);
                    const label = val === 'fresher' ? 'Fresher (0-1 Yrs)' : 'Experienced (1-3 Yrs)';
                    window.showToast(`Experience filter set to: ${label}`, 'success');
                }
            }
        });
    }

    // 9. Window Controls
    document.getElementById('btn-min')?.addEventListener('click', () => window.electronAPI?.minimize());
    document.getElementById('btn-max')?.addEventListener('click', () => window.electronAPI?.maximize());
    document.getElementById('btn-close')?.addEventListener('click', () => window.electronAPI?.close());

    // 10. Live Config Sync Event from AI Agent
    if (window.electronAPI && window.electronAPI.onConfigUpdated) {
        window.electronAPI.onConfigUpdated((newConfig) => {
            window.appState.config = newConfig;
            if (locSelector && newConfig.primary_location) {
                const p = newConfig.primary_location.toLowerCase();
                for (let opt of locSelector.options) {
                    if (p.includes(opt.value.toLowerCase())) { locSelector.value = opt.value; break; }
                }
            }
            if (expSelector && newConfig.experience_level) {
                expSelector.value = newConfig.experience_level;
            }
            if (window.location.hash === '#settings' && window.SettingsPage) {
                const container = document.getElementById('page-container');
                if (container) {
                    container.innerHTML = window.SettingsPage.render();
                    if (window.SettingsPage.init) window.SettingsPage.init();
                }
            }
        });
    }

    navigate();
});
