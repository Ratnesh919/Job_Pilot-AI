window.DashboardPage = {
    render: () => {
        return `
            <div class="dashboard-page" style="display: flex; flex-direction: column; gap: 20px;">
                <!-- Setup Welcome Banner if not configured -->
                <div id="dash-setup-banner" style="display: none; background: linear-gradient(135deg, rgba(59,130,246,0.12), rgba(139,92,246,0.12)); border: 1px solid #3b82f640; border-radius: 12px; padding: 18px 22px; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700; color: #fff; font-size: 14px;">👋 Welcome to JobPilot-AI! Let's get you set up</div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Add your resume, target roles, and free API keys to enable autonomous applications.</div>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <a href="#guide" class="btn btn-secondary" style="font-size: 12px; padding: 8px 14px;">View Guide</a>
                        <a href="#settings" class="btn btn-primary" style="font-size: 12px; padding: 8px 14px;">Configure Settings ⚙️</a>
                    </div>
                </div>

                <!-- Top 5 Stats Row -->
                <div class="stats-grid" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px;">
                    <div class="stat-card" style="background: #141a29; padding: 18px; border-radius: 10px; border: 1px solid #232d42;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; color: #94a3b8; font-weight: 500;">Applications Sent</span>
                            <span style="font-size: 11px; color: #10b981; font-weight: 600;">Active</span>
                        </div>
                        <div class="value" id="dash-sent" style="font-size: 26px; font-weight: 700; color: #fff; margin-top: 6px;">0</div>
                    </div>
                    <div class="stat-card" style="background: #141a29; padding: 18px; border-radius: 10px; border: 1px solid #232d42;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; color: #94a3b8; font-weight: 500;">In Progress</span>
                            <span style="font-size: 11px; color: #3b82f6; font-weight: 600;">Running</span>
                        </div>
                        <div class="value" id="dash-progress" style="font-size: 26px; font-weight: 700; color: #fff; margin-top: 6px;">0</div>
                    </div>
                    <div class="stat-card" style="background: #141a29; padding: 18px; border-radius: 10px; border: 1px solid #232d42;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; color: #94a3b8; font-weight: 500;">Under Review</span>
                            <span style="font-size: 11px; color: #f59e0b; font-weight: 600;">Screening</span>
                        </div>
                        <div class="value" id="dash-responses" style="font-size: 26px; font-weight: 700; color: #f59e0b; margin-top: 6px;">0</div>
                    </div>
                    <div class="stat-card" style="background: #141a29; padding: 18px; border-radius: 10px; border: 1px solid #232d42;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; color: #94a3b8; font-weight: 500;">Interviews</span>
                            <span style="font-size: 11px; color: #10b981; font-weight: 600;">🎉 High Priority</span>
                        </div>
                        <div class="value" id="dash-interviews" style="font-size: 26px; font-weight: 700; color: #10b981; margin-top: 6px;">0</div>
                    </div>
                    <div class="stat-card" style="background: #141a29; padding: 18px; border-radius: 10px; border: 1px solid #232d42;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; color: #94a3b8; font-weight: 500;">Success Rate</span>
                            <span style="font-size: 11px; color: #3b82f6; font-weight: 600;">Positive</span>
                        </div>
                        <div class="value" id="dash-success" style="font-size: 26px; font-weight: 700; color: #3b82f6; margin-top: 6px;">0%</div>
                    </div>
                </div>

                <!-- Middle Section: Table + Feed -->
                <div class="middle-section" style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
                    <!-- Recent Applications -->
                    <div class="card" style="background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 20px; display: flex; flex-direction: column;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <h3 style="margin: 0; font-size: 15px; font-weight: 600; color: #fff;">Recent Auto-Applications</h3>
                            <a href="#tracker" style="font-size: 12px; color: #3b82f6; text-decoration: none; font-weight: 600;">View All ↗</a>
                        </div>
                        <div id="dash-recent-table" style="flex: 1; overflow-y: auto; max-height: 280px;">
                            <!-- Populated dynamically -->
                            <div style="color: #94a3b8; font-size: 13px; text-align: center; padding: 40px 0;">No applications dispatched yet. Start the bot below!</div>
                        </div>
                    </div>

                    <!-- Live Terminal Output Stream -->
                    <div class="card" style="background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 20px; display: flex; flex-direction: column;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="status-dot inactive" id="dash-terminal-dot"></span>
                                <h3 style="margin: 0; font-size: 15px; font-weight: 600; color: #fff;">Live Agent Stream</h3>
                            </div>
                            <span style="font-size: 11px; color: #94a3b8; font-family: monospace;" id="dash-stream-mode">IDLE</span>
                        </div>
                        <div id="dash-terminal-box" style="flex: 1; background: #080c13; border: 1px solid #232d42; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 11px; color: #10b981; overflow-y: auto; max-height: 280px; min-height: 200px; white-space: pre-wrap; line-height: 1.4;">
JobPilot-AI Ready.
Click 'Start Bot' to begin autonomous multi-portal job applications.
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init: () => {
        // Check if configuration needs initial setup
        const cfg = window.appState?.config || {};
        const banner = document.getElementById('dash-setup-banner');
        if (banner) {
            const needsSetup = !cfg.email?.sender || !cfg.api_keys?.openrouter;
            banner.style.display = needsSetup ? 'flex' : 'none';
        }

        // Render stats
        const stats = window.appState?.stats || {};
        const sentEl = document.getElementById('dash-sent');
        const progEl = document.getElementById('dash-progress');
        const respEl = document.getElementById('dash-responses');
        const intEl = document.getElementById('dash-interviews');
        const succEl = document.getElementById('dash-success');

        if (sentEl) sentEl.textContent = stats.totalApplications || '0';
        if (progEl) progEl.textContent = stats.applied || '0';
        if (respEl) respEl.textContent = stats.underReview || '0';
        if (intEl) intEl.textContent = stats.interviews || '0';
        if (succEl) succEl.textContent = stats.successRate || '0%';

        // Render recent applications table
        const apps = window.appState?.applications || [];
        const tableBox = document.getElementById('dash-recent-table');
        if (tableBox && apps.length > 0) {
            tableBox.innerHTML = `
                <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid #232d42; color: #94a3b8;">
                            <th style="padding: 8px 4px;">Company</th>
                            <th style="padding: 8px 4px;">Role</th>
                            <th style="padding: 8px 4px;">Platform</th>
                            <th style="padding: 8px 4px;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${apps.slice(0, 6).map(a => `
                            <tr style="border-bottom: 1px solid #1a2236; cursor: pointer;" onclick="window.openApplicationModal(${JSON.stringify(a).replace(/"/g, '&quot;')})">
                                <td style="padding: 8px 4px; font-weight: 600; color: #fff;">${a.company || 'Company'}</td>
                                <td style="padding: 8px 4px; color: #cbd5e1;">${a.role || 'Software Engineer'}</td>
                                <td style="padding: 8px 4px; color: #94a3b8;">${a.platform || 'Portal'}</td>
                                <td style="padding: 8px 4px;">${window.getStatusBadge(a.status)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }

        // Bot live terminal output listener
        const termBox = document.getElementById('dash-terminal-box');
        const termDot = document.getElementById('dash-terminal-dot');
        const termMode = document.getElementById('dash-stream-mode');

        if (window.electronAPI && window.electronAPI.onBotOutput) {
            window.electronAPI.onBotOutput((data) => {
                if (termBox) {
                    termBox.textContent += '\n' + data.text;
                    termBox.scrollTop = termBox.scrollHeight;
                }
                if (termDot) termDot.className = 'status-dot active';
                if (termMode) termMode.textContent = 'RUNNING';
            });
        }
    }
};
