window.TrackerPage = {
    render: () => {
        return `
            <div class="tracker-page" style="display: flex; flex-direction: column; gap: 20px;">
                <!-- Header Controls -->
                <div style="display: flex; justify-content: space-between; align-items: center; background: #141a29; padding: 14px 20px; border-radius: 12px; border: 1px solid #232d42;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <input type="text" id="tracker-search" placeholder="Search company, role, or portal..." style="padding: 8px 14px; background: #0c101a; border: 1px solid #232d42; color: #fff; border-radius: 6px; font-size: 13px; width: 260px; outline: none;">
                        <select id="tracker-filter-status" style="padding: 8px 12px; background: #0c101a; border: 1px solid #232d42; color: #cbd5e1; border-radius: 6px; font-size: 13px; outline: none;">
                            <option value="all">All Statuses</option>
                            <option value="Applied">Applied</option>
                            <option value="Under Review">Under Review</option>
                            <option value="Assessment / Test">Assessment / Test</option>
                            <option value="Interview Scheduled">Interview Scheduled</option>
                            <option value="Selected / Offered">Selected / Offered</option>
                            <option value="Rejected">Rejected</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="tracker-view-table" class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;">Table View</button>
                        <button id="tracker-scan-inbox" class="btn btn-primary" style="padding: 6px 14px; font-size: 12px;">Scan Gmail Updates</button>
                    </div>
                </div>

                <!-- Applications Table -->
                <div style="background: #141a29; border: 1px solid #232d42; border-radius: 12px; padding: 16px; overflow-x: auto;">
                    <div id="tracker-table-container">
                        <!-- Populated dynamically -->
                    </div>
                </div>
            </div>
        `;
    },

    init: () => {
        const searchInput = document.getElementById('tracker-search');
        const filterSelect = document.getElementById('tracker-filter-status');
        const scanBtn = document.getElementById('tracker-scan-inbox');
        const container = document.getElementById('tracker-table-container');

        function renderTable() {
            const apps = window.appState?.applications || [];
            const query = searchInput?.value.toLowerCase().trim() || '';
            const statusFilter = filterSelect?.value || 'all';

            const filtered = apps.filter(a => {
                const matchQuery = !query || 
                    (a.company && a.company.toLowerCase().includes(query)) ||
                    (a.role && a.role.toLowerCase().includes(query)) ||
                    (a.platform && a.platform.toLowerCase().includes(query));
                const matchStatus = statusFilter === 'all' || a.status === statusFilter;
                return matchQuery && matchStatus;
            });

            if (filtered.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #94a3b8; font-size: 13px;">
                        No matching job applications found.
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid #232d42; color: #94a3b8; font-size: 12px;">
                            <th style="padding: 10px 8px;">Company</th>
                            <th style="padding: 10px 8px;">Role</th>
                            <th style="padding: 10px 8px;">Platform</th>
                            <th style="padding: 10px 8px;">Applied Date</th>
                            <th style="padding: 10px 8px;">Status</th>
                            <th style="padding: 10px 8px; text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${filtered.map(a => `
                            <tr style="border-bottom: 1px solid #1a2236; transition: background 0.15s;" onmouseover="this.style.background='#1a2236'" onmouseout="this.style.background='transparent'">
                                <td style="padding: 12px 8px; font-weight: 600; color: #fff;">${a.company || 'Company'}</td>
                                <td style="padding: 12px 8px; color: #cbd5e1;">${a.role || 'Software Engineer'}</td>
                                <td style="padding: 12px 8px; color: #94a3b8;">${a.platform || 'Portal'}</td>
                                <td style="padding: 12px 8px; color: #64748b; font-size: 12px;">${a.applied_date || 'Recent'}</td>
                                <td style="padding: 12px 8px;">${window.getStatusBadge(a.status)}</td>
                                <td style="padding: 12px 8px; text-align: right;">
                                    <button class="btn btn-secondary" onclick="window.openApplicationModal(${JSON.stringify(a).replace(/"/g, '&quot;')})" style="padding: 4px 10px; font-size: 11px; border-radius: 4px;">Details</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }

        searchInput?.addEventListener('input', renderTable);
        filterSelect?.addEventListener('change', renderTable);

        scanBtn?.addEventListener('click', async () => {
            scanBtn.textContent = 'Scanning Gmail...';
            scanBtn.disabled = true;
            if (window.electronAPI && window.electronAPI.checkStatusUpdates) {
                const res = await window.electronAPI.checkStatusUpdates();
                window.showToast(res.message, res.success ? 'success' : 'info');
                if (window.electronAPI.getApplications) {
                    window.appState.applications = await window.electronAPI.getApplications();
                    renderTable();
                }
            }
            scanBtn.textContent = 'Scan Gmail Updates';
            scanBtn.disabled = false;
        });

        renderTable();
    }
};
