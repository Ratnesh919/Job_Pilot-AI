document.addEventListener('DOMContentLoaded', async () => {
    // 1. State Management
    window.appState = {
        config: null,
        stats: null,
        applications: [],
        notifications: [],
        botStatus: { running: false, startTime: null, appliedCount: 0, errors: 0 },
        liveOutput: []
    };

    const mainContent = document.getElementById('page-content');

    // 2. Utility Functions
    window.formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}h ${m}m`;
        if (m > 0) return `${m}m ${s}s`;
        return `${s}s`;
    };

    window.formatDate = (dateStr) => {
        if (!dateStr) return 'Recent';
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHrs = Math.floor(diffMins / 60);
        if (diffHrs < 24) return `${diffHrs}h ago`;
        return `${Math.floor(diffHrs / 24)}d ago`;
    };

    window.getStatusBadge = (status) => {
        let bg = 'rgba(59, 130, 246, 0.15)';
        let color = '#60a5fa';
        let border = 'rgba(59, 130, 246, 0.3)';
        let icon = '•';

        if (status === 'Interview Scheduled' || (status && status.includes('INTERVIEW'))) {
            bg = 'rgba(16, 185, 129, 0.15)';
            color = '#34d399';
            border = 'rgba(16, 185, 129, 0.3)';
            icon = '🎉';
        } else if (status === 'Selected / Offered' || (status && status.includes('OFFER'))) {
            bg = 'rgba(6, 182, 212, 0.15)';
            color = '#22d3ee';
            border = 'rgba(6, 182, 212, 0.3)';
            icon = '🏆';
        } else if (status === 'Under Review' || (status && status.includes('REVIEW'))) {
            bg = 'rgba(245, 158, 11, 0.15)';
            color = '#fbbf24';
            border = 'rgba(245, 158, 11, 0.3)';
            icon = '⏳';
        } else if (status === 'Assessment / Test' || (status && status.includes('TEST'))) {
            bg = 'rgba(139, 92, 246, 0.15)';
            color = '#a78bfa';
            border = 'rgba(139, 92, 246, 0.3)';
            icon = '📝';
        } else if (status === 'Rejected' || (status && status.includes('REJECTED'))) {
            bg = 'rgba(239, 68, 68, 0.15)';
            color = '#f87171';
            border = 'rgba(239, 68, 68, 0.3)';
            icon = '✕';
        }

        return `<span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 14px; font-size: 12px; font-weight: 600; background: ${bg}; color: ${color}; border: 1px solid ${border};">${icon} ${status}</span>`;
    };

    window.showToast = (message, type = 'info') => {
        const toast = document.createElement('div');
        let bg = '#1a1f2e';
        let border = '#3b82f6';
        if (type === 'success') border = '#10b981';
        if (type === 'error') border = '#ef4444';
        if (type === 'warning') border = '#f59e0b';
        
        toast.style.cssText = `
            position: fixed; bottom: 24px; right: 24px; 
            background: ${bg}; color: white; border-left: 4px solid ${border};
            padding: 14px 20px; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            z-index: 9999; font-family: Inter, sans-serif; font-size: 13px; font-weight: 500;
            transition: all 0.3s ease; border: 1px solid #2a3142; border-left: 4px solid ${border};
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    };

    // 3. Page Registry & SPA Router
    const routes = {
        '#dashboard': window.DashboardPage,
        '#ai-agent': window.AiAgentPage,
        '#tracker': window.TrackerPage,
        '#applications': window.TrackerPage,
        '#live-monitor': window.LiveMonitorPage,
        '#settings': window.SettingsPage,
        '#activity-log': window.ActivityLogPage
    };

    function navigate() {
        let hash = window.location.hash || '#dashboard';
        if (hash === '#applications') hash = '#tracker';
        
        const page = routes[hash] || window.DashboardPage;
        if (page && mainContent) {
            mainContent.innerHTML = page.render();
            if (page.init) page.init();
            
            // Update sidebar active states
            document.querySelectorAll('.sidebar-nav a').forEach(el => {
                const h = el.getAttribute('href');
                if (h === hash || (h === '#tracker' && hash === '#applications')) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            });
        }
    }

    window.addEventListener('hashchange', navigate);

    // 4. Application Details & Status History Modal
    window.openApplicationModal = (appData, onUpdated) => {
        const overlay = document.getElementById('app-modal-overlay');
        const companyEl = document.getElementById('modal-company');
        const roleEl = document.getElementById('modal-role');
        const statusBadgeEl = document.getElementById('modal-status-badge');
        const platformEl = document.getElementById('modal-platform');
        const statusSelect = document.getElementById('modal-status-select');
        const noteInput = document.getElementById('modal-note-input');
        const historyList = document.getElementById('modal-history-list');
        const updateBtn = document.getElementById('modal-update-btn');
        const closeBtn = document.getElementById('modal-close-btn');

        if (!overlay) return;

        companyEl.textContent = appData.company || 'Company';
        roleEl.textContent = appData.role || 'Job Position';
        statusBadgeEl.innerHTML = window.getStatusBadge(appData.status || 'Applied');
        platformEl.textContent = appData.platform || 'Portal / Direct';
        statusSelect.value = appData.status || 'Applied';
        noteInput.value = '';

        // Render timeline history
        const history = appData.history || [];
        if (history.length === 0) {
            historyList.innerHTML = `<div style="color: #94a3b8; font-size: 13px;">No history updates recorded yet.</div>`;
        } else {
            historyList.innerHTML = history.slice().reverse().map(h => `
                <div style="position: relative; padding-bottom: 12px; margin-left: 12px;">
                    <div style="position: absolute; left: -19px; top: 3px; width: 10px; height: 10px; border-radius: 50%; background: #3b82f6;"></div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; font-size: 13px; color: #fff;">${h.status}</span>
                        <span style="font-size: 11px; color: #64748b;">${h.date}</span>
                    </div>
                    <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">${h.note || 'Status updated'}</div>
                </div>
            `).join('');
        }

        overlay.style.display = 'flex';

        // Update button
        updateBtn.onclick = async () => {
            const newStatus = statusSelect.value;
            const note = noteInput.value.trim();
            if (window.electronAPI && window.electronAPI.updateApplicationStatus) {
                const res = await window.electronAPI.updateApplicationStatus({
                    id: appData.id,
                    status: newStatus,
                    note: note || `Manually marked as ${newStatus}`
                });
                if (res.success) {
                    window.showToast(`Updated ${appData.company} status to "${newStatus}"`, 'success');
                    overlay.style.display = 'none';
                    if (onUpdated) onUpdated();
                    navigate();
                } else {
                    window.showToast('Failed to update status', 'error');
                }
            }
        };

        closeBtn.onclick = () => { overlay.style.display = 'none'; };
        overlay.onclick = (e) => { if (e.target === overlay) overlay.style.display = 'none'; };
    };

    // 5. Notifications Drawer & Badge
    async function loadNotifications() {
        if (window.electronAPI && window.electronAPI.getNotifications) {
            window.appState.notifications = await window.electronAPI.getNotifications();
            renderNotificationsUI();
        }
    }

    function renderNotificationsUI() {
        const badge = document.getElementById('notif-badge');
        const list = document.getElementById('notif-list');
        const notifs = window.appState.notifications || [];
        const unreadCount = notifs.filter(n => !n.read).length;

        if (badge) {
            if (unreadCount > 0) {
                badge.style.display = 'flex';
                badge.textContent = unreadCount > 9 ? '9+' : unreadCount;
            } else {
                badge.style.display = 'none';
            }
        }

        if (list) {
            if (notifs.length === 0) {
                list.innerHTML = `<div style="padding: 24px; text-align: center; color: #94a3b8; font-size: 13px;">No notifications yet.</div>`;
                return;
            }

            list.innerHTML = notifs.map(n => {
                let dotColor = '#3b82f6';
                if (n.type === 'success') dotColor = '#10b981';
                if (n.type === 'error') dotColor = '#ef4444';
                if (n.type === 'warning') dotColor = '#f59e0b';

                return `
                    <div style="padding: 14px 18px; border-bottom: 1px solid #232a3b; transition: background 0.2s;" onmouseover="this.style.background='#1f2638'" onmouseout="this.style.background='transparent'">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="width: 8px; height: 8px; border-radius: 50%; background: ${dotColor};"></span>
                                <span style="font-weight: 600; font-size: 13px; color: #fff;">${n.title}</span>
                            </div>
                            <span style="font-size: 11px; color: #64748b;">${window.formatDate(n.timestamp)}</span>
                        </div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 5px; line-height: 1.4;">${n.body}</div>
                    </div>
                `;
            }).join('');
        }
    }

    const notifBtn = document.getElementById('notif-bell-btn');
    const notifDropdown = document.getElementById('notif-dropdown');
    const clearNotifsBtn = document.getElementById('clear-notifs-btn');

    notifBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = notifDropdown.style.display === 'block';
        notifDropdown.style.display = isOpen ? 'none' : 'block';
    });

    document.addEventListener('click', (e) => {
        if (notifDropdown && !notifDropdown.contains(e.target) && e.target !== notifBtn) {
            notifDropdown.style.display = 'none';
        }
    });

    clearNotifsBtn?.addEventListener('click', async () => {
        if (window.electronAPI && window.electronAPI.clearNotifications) {
            await window.electronAPI.clearNotifications();
            window.appState.notifications = [];
            renderNotificationsUI();
        }
    });

    // 6. Global Quick Scan Button in Topbar
    const globalSyncBtn = document.getElementById('global-sync-btn');
    globalSyncBtn?.addEventListener('click', async () => {
        globalSyncBtn.disabled = true;
        globalSyncBtn.innerHTML = '<span class="spinner" style="width: 12px; height: 12px; display: inline-block; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></span> <span>Scanning...</span>';
        
        if (window.electronAPI && window.electronAPI.checkStatusUpdates) {
            try {
                const res = await window.electronAPI.checkStatusUpdates();
                if (res.success) {
                    window.showToast(res.message || 'Status check complete!', 'success');
                } else {
                    window.showToast(res.error || 'Failed to scan inbox.', 'error');
                }
            } catch (e) {
                window.showToast('Scan error: ' + e.message, 'error');
            }
        }
        await loadNotifications();
        globalSyncBtn.disabled = false;
        globalSyncBtn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg><span>Scan Updates</span>';
        navigate();
    });

    // 7. Initial Load & IPC Setup
    if (window.electronAPI) {
        try {
            window.appState.config = await window.electronAPI.getConfig();
            window.appConfig = window.appState.config;

            // Setup bot callbacks
            window.electronAPI.onBotOutput((line) => {
                window.appState.liveOutput.push(line);
                const term = document.getElementById('terminal-output');
                if (term) {
                    const div = document.createElement('div');
                    div.textContent = line;
                    term.appendChild(div);
                    term.scrollTop = term.scrollHeight;
                }
            });

            window.electronAPI.onBotStatusChange((status) => {
                window.appState.botStatus = status;
                updateSidebarBotStatus();
            });

            window.electronAPI.onNewNotification((notif) => {
                window.appState.notifications.unshift(notif);
                renderNotificationsUI();
                window.showToast(notif.title + ' — ' + notif.body.substring(0, 50), notif.type || 'info');
            });

            await loadNotifications();
        } catch (e) {
            console.warn("Electron API initialization warning:", e);
        }
    }

    navigate(); // Render initial page

    // 8. Window Controls
    document.getElementById('btn-minimize')?.addEventListener('click', () => window.electronAPI?.minimize?.());
    document.getElementById('btn-maximize')?.addEventListener('click', () => window.electronAPI?.maximize?.());
    document.getElementById('btn-close')?.addEventListener('click', () => window.electronAPI?.close?.());

    // 9. Sidebar Bot Status Panel Update
    function updateSidebarBotStatus() {
        const btn = document.getElementById('bot-toggle-btn');
        const runtimeEl = document.getElementById('bot-runtime');
        const appliedEl = document.getElementById('bot-applied');
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.getElementById('bot-status-text');
        
        if (window.appState.botStatus.running) {
            if (btn) {
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Stop Bot</span>';
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-danger');
            }
            if (statusDot) { statusDot.className = 'status-dot active'; }
            if (statusText) statusText.textContent = 'Active';
        } else {
            if (btn) {
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>Start Bot</span>';
                btn.classList.remove('btn-danger');
                btn.classList.add('btn-primary');
            }
            if (statusDot) { statusDot.className = 'status-dot inactive'; }
            if (statusText) statusText.textContent = 'Idle';
            if (runtimeEl) runtimeEl.textContent = '0m 0s';
        }
        if (appliedEl) appliedEl.textContent = window.appState.botStatus.appliedCount || 0;
    }

    // Status polling
    setInterval(async () => {
        if (window.electronAPI && window.electronAPI.getBotStatus) {
            const status = await window.electronAPI.getBotStatus();
            window.appState.botStatus = status;
            
            if (status.running && status.startTime) {
                const elapsed = Math.floor((Date.now() - status.startTime) / 1000);
                const runtimeEl = document.getElementById('bot-runtime');
                if (runtimeEl) runtimeEl.textContent = window.formatTime(elapsed);
            }
        }
    }, 1000);

    // Login Prompt Modal Controller
    window.showLoginPromptModal = (status) => {
        const modal = document.getElementById('login-prompt-modal');
        const linkedinBadge = document.getElementById('login-modal-linkedin-badge');
        const naukriBadge = document.getElementById('login-modal-naukri-badge');
        const openChromeBtn = document.getElementById('btn-login-modal-open-chrome');
        const skipBtn = document.getElementById('btn-login-modal-skip');

        if (!modal) return;

        if (linkedinBadge) {
            if (status.linkedin) {
                linkedinBadge.textContent = 'LinkedIn: Logged In ✓';
                linkedinBadge.style.background = '#10b98120';
                linkedinBadge.style.color = '#34d399';
                linkedinBadge.style.borderColor = '#10b98140';
            } else {
                linkedinBadge.textContent = 'LinkedIn: Not Logged In ✕';
                linkedinBadge.style.background = '#ef444420';
                linkedinBadge.style.color = '#f87171';
                linkedinBadge.style.borderColor = '#ef444440';
            }
        }

        if (naukriBadge) {
            if (status.naukri) {
                naukriBadge.textContent = 'Naukri: Logged In ✓';
                naukriBadge.style.background = '#10b98120';
                naukriBadge.style.color = '#34d399';
                naukriBadge.style.borderColor = '#10b98140';
            } else {
                naukriBadge.textContent = 'Naukri: Not Logged In ✕';
                naukriBadge.style.background = '#ef444420';
                naukriBadge.style.color = '#f87171';
                naukriBadge.style.borderColor = '#ef444440';
            }
        }

        modal.style.display = 'flex';

        if (openChromeBtn) {
            openChromeBtn.onclick = async () => {
                modal.style.display = 'none';
                window.showToast('Opening Chrome. Log in to your accounts and close browser when done.', 'info');
                if (window.electronAPI && window.electronAPI.openLoginBrowser) {
                    await window.electronAPI.openLoginBrowser();
                }
            };
        }

        if (skipBtn) {
            skipBtn.onclick = async () => {
                modal.style.display = 'none';
                const result = await window.electronAPI.startBot({ headless: true });
                window.showToast(result.message, result.success ? 'success' : 'error');
                if (result.success) window.location.hash = '#live-monitor';
            };
        }

        modal.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };
    };

    // 10. Bot Toggle Button
    document.getElementById('bot-toggle-btn')?.addEventListener('click', async () => {
        if (!window.electronAPI) return;
        if (window.appState.botStatus.running) {
            const result = await window.electronAPI.stopBot();
            window.showToast(result.message, result.success ? 'success' : 'error');
        } else {
            // Check if portals are logged in
            if (window.electronAPI.checkLoginStatus) {
                const status = await window.electronAPI.checkLoginStatus();
                if (status.needs_login) {
                    window.showLoginPromptModal(status);
                    return;
                }
            }
            // IMPORTANT: Always run headed (headless: false) — portals detect & block headless browsers
            const result = await window.electronAPI.startBot({ headless: false });
            window.showToast(result.message, result.success ? 'success' : 'error');
            if (result.success) {
                window.location.hash = '#live-monitor';
            }
        }
    });

    // Real-time bot status push from main process
    if (window.electronAPI && window.electronAPI.onBotStatusChange) {
        window.electronAPI.onBotStatusChange((status) => {
            window.appState.botStatus = { ...window.appState.botStatus, ...status };
            updateSidebarBotStatus();
            // Update runtime counter
            if (status.running && status.startTime) {
                const elapsed = Math.floor((Date.now() - status.startTime) / 1000);
                const runtimeEl = document.getElementById('bot-runtime');
                if (runtimeEl) runtimeEl.textContent = window.formatTime(elapsed);
            }
            // Update jobs applied counter immediately
            const appliedEl = document.getElementById('bot-applied');
            if (appliedEl && status.appliedCount !== undefined) {
                appliedEl.textContent = status.appliedCount;
            }
            // Success rate
            const srEl = document.getElementById('bot-success-rate');
            if (srEl && status.appliedCount > 0) {
                srEl.textContent = '100%';
            }
        });
    }

    // 11. Sidebar Navigation Active States
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });

    // 12. Universal Topbar AI Prompt Bar Handler
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
    universalInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleUniversalPrompt();
    });

    // 13. Global Experience Level Mode Selector (Fresher vs Experienced)
    const expSelector = document.getElementById('global-exp-selector');
    if (expSelector) {
        if (window.appState.config && window.appState.config.experience_level) {
            expSelector.value = window.appState.config.experience_level;
        }
        expSelector.addEventListener('change', async (e) => {
            const val = e.target.value;
            if (window.appState.config) {
                window.appState.config.experience_level = val;
                if (window.electronAPI && window.electronAPI.saveConfig) {
                    await window.electronAPI.saveConfig(window.appState.config);
                    const label = val === 'fresher' ? 'Fresher / Entry-Level (0-1 Yrs)' : 'Experienced (1-3 Yrs)';
                    window.showToast(`Target filter set to: ${label}`, 'success');
                }
            }
        });
    }

    // 14. Global Preferred Location Selector
    const locSelector = document.getElementById('global-loc-selector');
    if (locSelector) {
        if (window.appState.config && window.appState.config.primary_location) {
            const primLoc = window.appState.config.primary_location;
            if (primLoc.includes('Kolkata')) locSelector.value = 'Kolkata';
            else if (primLoc.includes('Bengaluru')) locSelector.value = 'Bengaluru';
            else if (primLoc.includes('Hyderabad')) locSelector.value = 'Hyderabad';
            else if (primLoc.includes('Pune')) locSelector.value = 'Pune';
            else if (primLoc.includes('Noida')) locSelector.value = 'Noida';
            else if (primLoc.includes('Remote')) locSelector.value = 'Remote';
        }
        locSelector.addEventListener('change', async (e) => {
            const val = e.target.value;
            if (window.appState.config) {
                window.appState.config.primary_location = val;
                if (window.electronAPI && window.electronAPI.saveConfig) {
                    await window.electronAPI.saveConfig(window.appState.config);
                    window.showToast(`Target location updated to: ${val}`, 'success');
                }
            }
        });
    }

    // 15. Real-Time Config Sync from AI Agent Commands
    if (window.electronAPI && window.electronAPI.onConfigUpdated) {
        window.electronAPI.onConfigUpdated((newConfig) => {
            window.appState.config = newConfig;

            // Sync Location selector
            if (locSelector && newConfig.primary_location) {
                const p = newConfig.primary_location;
                if (p.includes('Kolkata')) locSelector.value = 'Kolkata';
                else if (p.includes('Bengaluru')) locSelector.value = 'Bengaluru';
                else if (p.includes('Hyderabad')) locSelector.value = 'Hyderabad';
                else if (p.includes('Pune')) locSelector.value = 'Pune';
                else if (p.includes('Noida')) locSelector.value = 'Noida';
                else if (p.includes('Remote')) locSelector.value = 'Remote';
            }

            // Sync Experience selector
            if (expSelector && newConfig.experience_level) {
                expSelector.value = newConfig.experience_level;
            }

            // If current page is settings, re-render to reflect changes
            if (window.location.hash === '#settings' && window.SettingsPage) {
                const container = document.getElementById('page-container');
                if (container) {
                    container.innerHTML = window.SettingsPage.render();
                    if (window.SettingsPage.init) window.SettingsPage.init();
                }
            }
        });
    }

    // 16. AI Resume Extracted Event
    if (window.electronAPI && window.electronAPI.onResumeExtracted) {
        window.electronAPI.onResumeExtracted(({ extracted, fileName }) => {
            const name = extracted.name || 'Candidate';
            const skillsStr = (extracted.skills || []).slice(0, 4).join(', ');
            window.showToast(`✨ AI Extracted Profile for ${name}! Skills: ${skillsStr}`, 'success');

            // Update user profile in sidebar
            const userNameEl = document.getElementById('user-name');
            const userEmailEl = document.getElementById('user-email');
            const userAvatarEl = document.getElementById('user-avatar');
            if (userNameEl && extracted.name) userNameEl.textContent = extracted.name;
            if (userEmailEl && extracted.email) userEmailEl.textContent = extracted.email;
            if (userAvatarEl && extracted.name) {
                userAvatarEl.textContent = extracted.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
            }

            navigate();
        });
    }
});
