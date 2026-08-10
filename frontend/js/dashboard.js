const Dashboard = {
    currentPage: 1,
    employeesMap: {},

    // Topic color palette
    TOPIC_COLORS: [
        { bg: 'linear-gradient(135deg,#1e3a5f,#3b82f6)', light: '#dbeafe', text: '#1e40af' },
        { bg: 'linear-gradient(135deg,#166534,#22c55e)', light: '#dcfce7', text: '#15803d' },
        { bg: 'linear-gradient(135deg,#6b21a8,#a855f7)', light: '#f3e8ff', text: '#7e22ce' },
        { bg: 'linear-gradient(135deg,#9a3412,#f97316)', light: '#ffedd5', text: '#c2410c' },
        { bg: 'linear-gradient(135deg,#0f4c75,#1565c0)', light: '#e3f2fd', text: '#1565c0' },
    ],

    init() {
        this.loadStats();
        this.loadEmployees(1);
        const searchInput = document.getElementById('empSearch');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => this.loadEmployees(1), 400));
        }
        const filterTopicEl = document.getElementById('filterTopic');
        const filterStatusEl = document.getElementById('filterStatus');
        if (filterTopicEl) filterTopicEl.addEventListener('change', () => this.loadEmployees(1));
        if (filterStatusEl) filterStatusEl.addEventListener('change', () => this.loadEmployees(1));

        // Smart auto-refresh every 10 seconds
        setInterval(() => {
            const searchVal = document.getElementById('empSearch')?.value || '';
            const empModal = document.getElementById('employeeModal');
            const attemptModal = document.getElementById('attemptDetailModal');
            
            const isEmpModalOpen = empModal && empModal.style.display === 'flex';
            const isAttemptModalOpen = !!attemptModal;

            if (!searchVal.trim() && !isEmpModalOpen && !isAttemptModalOpen) {
                console.log("Dashboard auto-refresh triggered...");
                Dashboard.loadStats();
                Dashboard.loadEmployees(Dashboard.currentPage || 1);
            }
        }, 10000);
    },



    async loadStats() {
        try {
            const stats = await API.getDashboardStats();

            // Main counters
            this.animateValue('kpi-total-employees', 0, stats.totalEmployees || 0, 900);
            this.animateValue('kpi-completed', 0, stats.completed || 0, 900);
            this.animateValue('kpi-active', 0, stats.active || 0, 900);

            // Topic stat cards
            const row = document.getElementById('topicStatsRow');
            if (!row) return;

            const topics = stats.topicStats || [];
            const cols = topics.length + 1; // +1 for total card
            row.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

            let html = '';

            topics.forEach((t, i) => {
                const color = this.TOPIC_COLORS[i % this.TOPIC_COLORS.length];
                const a1 = t.avg1 !== null ? t.avg1 + '%' : '—';
                const a2 = t.avg2 !== null ? t.avg2 + '%' : '—';
                const diffVal = t.diff !== null ? t.diff : null;

                html += `
                <div style="background:${color.bg};border-radius:14px;padding:16px;color:#fff;box-shadow:0 4px 16px rgba(0,0,0,0.15);position:relative;overflow:hidden;">
                    <div style="position:absolute;top:-10px;right:-10px;font-size:60px;opacity:0.1;">📊</div>
                    <div style="font-size:13px;font-weight:700;margin-bottom:12px;opacity:0.95;line-height:1.4;">${t.name || (t.seq + '-Мавзу')}</div>
                    <div style="display:flex;flex-direction:column;gap:6px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.15);border-radius:8px;padding:6px 10px;">
                            <span style="font-size:11px;opacity:0.8;">1-уриниш ўртача</span>
                            <span style="font-size:16px;font-weight:800;">${a1}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.15);border-radius:8px;padding:6px 10px;">
                            <span style="font-size:11px;opacity:0.8;">2-уриниш ўртача</span>
                            <span style="font-size:16px;font-weight:800;">${a2}</span>
                        </div>
                        ${diffVal !== null ? `
                        <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.2);border-radius:8px;padding:6px 10px;">
                            <span style="font-size:11px;opacity:0.8;">Ўсиш</span>
                            <span style="font-size:14px;font-weight:800;">${diffVal > 0 ? '+' : ''}${diffVal}%</span>
                        </div>` : ''}
                    </div>
                </div>`;
            });

            // Total "Jami yakuni" card
            const ta1 = stats.overallAvg1 !== null && stats.overallAvg1 !== undefined ? stats.overallAvg1 + '%' : '—';
            const ta2 = stats.overallAvg2 !== null && stats.overallAvg2 !== undefined ? stats.overallAvg2 + '%' : '—';
            const td = stats.overallDiff;
            html += `
            <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:14px;padding:16px;color:#fff;box-shadow:0 4px 16px rgba(0,0,0,0.25);position:relative;overflow:hidden;border:1px solid rgba(255,255,255,0.1);">
                <div style="position:absolute;top:-10px;right:-10px;font-size:60px;opacity:0.08;">🏆</div>
                <div style="font-size:11px;font-weight:700;letter-spacing:1px;opacity:0.7;margin-bottom:8px;">ЖАМИ ЯКУНИ</div>
                <div style="font-size:13px;font-weight:600;margin-bottom:12px;opacity:0.8;">Барча мавзулар бўйича</div>
                <div style="display:flex;flex-direction:column;gap:6px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.08);border-radius:8px;padding:6px 10px;">
                        <span style="font-size:11px;opacity:0.7;">1-уринишлар ўртача</span>
                        <span style="font-size:16px;font-weight:800;color:#60a5fa;">${ta1}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.08);border-radius:8px;padding:6px 10px;">
                        <span style="font-size:11px;opacity:0.7;">2-уринишлар ўртача</span>
                        <span style="font-size:16px;font-weight:800;color:#34d399;">${ta2}</span>
                    </div>
                    ${td !== null && td !== undefined ? `
                    <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.12);border-radius:8px;padding:6px 10px;">
                        <span style="font-size:11px;opacity:0.7;">Умумий ўсиш</span>
                        <span style="font-size:14px;font-weight:800;color:${td > 0 ? '#4ade80' : '#f87171'};">${td > 0 ? '+' : ''}${td}%</span>
                    </div>` : ''}
                </div>
            </div>`;

            row.innerHTML = html;

        } catch (e) {
            console.error('Stats load error:', e);
        }
    },

    buildHeader(topicCount) {
        const GH = 'background:#15803d;color:#fff;text-align:center;padding:10px 6px;border:1px solid #166534;white-space:nowrap;font-size:12px;font-weight:700;';
        const GS = 'background:#22c55e;color:#fff;text-align:center;padding:7px 4px;border:1px solid #166534;white-space:nowrap;font-size:11px;font-weight:600;';
        const GD = 'background:#1e3a5f;color:#fff;text-align:center;padding:10px 6px;border:1px solid #1e40af;white-space:nowrap;font-size:12px;font-weight:700;';
        const GDS = 'background:#2563eb;color:#fff;text-align:center;padding:7px 4px;border:1px solid #1e40af;white-space:nowrap;font-size:11px;font-weight:600;';

        let row1 = `<tr>
            <th rowspan="2" style="${GH}width:40px;">№</th>
            <th rowspan="2" style="${GH}min-width:160px;text-align:left;padding-left:12px;">Ф.И.Ш.</th>
            <th rowspan="2" style="${GH}min-width:170px;text-align:left;padding-left:8px;">Филиал</th>`;
        let row2 = '<tr>';

        for (let i = 1; i <= topicCount; i++) {
            row1 += `<th colspan="4" style="${GH}">${i}-Мавзу</th>`;
            row2 += `<th style="${GS}">1-уриниш</th><th style="${GS}">2-уриниш</th><th style="${GS}">Фарқ</th><th style="${GS}">Ҳолат</th>`;
        }

        row1 += `<th colspan="3" style="${GD}">Жами якуни</th>`;
        row2 += `<th style="${GDS}">1-ур ўртача</th><th style="${GDS}">2-ур ўртача</th><th style="${GDS}">Фарқ</th>`;

        row1 += '</tr>';
        row2 += '</tr>';
        return row1 + row2;
    },

    async loadEmployees(page = 1) {
        this.currentPage = page;
        try {
            const search = (document.getElementById('empSearch')?.value || '').trim().toLowerCase();
            const filterTopic = document.getElementById('filterTopic')?.value || 'all';
            const filterStatus = document.getElementById('filterStatus')?.value || 'all';

            // Fetch all items (up to 1000) to allow clean multi-criteria filtering client-side
            const data = await API.getDashboardEmployees({ page: 1, page_size: 1000 });
            const thead = document.getElementById('ratingTableHead');
            const tbody = document.getElementById('employeesTableBody');

            if (!data || !data.items || data.items.length === 0) {
                this.employeesMap = {};
                const tc = 4;
                const colspan = 3 + tc * 4 + 3;
                if (thead) thead.innerHTML = this.buildHeader(tc);
                if (tbody) tbody.innerHTML = `
                    <tr><td colspan="${colspan}" style="text-align:center;padding:48px;color:#9ca3af;">
                        <div style="font-size:40px;margin-bottom:12px;">📋</div>
                        <div style="font-size:16px;font-weight:600;">Ходимлар рўйхати бўш</div>
                    </td></tr>`;
                return;
            }

            // Cache employee map
            this.employeesMap = {};
            data.items.forEach(emp => {
                this.employeesMap[emp.id] = emp;
            });

            // Filter items client-side
            let filtered = data.items;

            // 1. Apply Search
            if (search) {
                filtered = filtered.filter(emp => 
                    (emp.name || '').toLowerCase().includes(search) || 
                    (emp.branch || '').toLowerCase().includes(search)
                );
            }

            // 2. Apply Topic & Attempt Status Filters
            if (filterTopic !== 'all' || filterStatus !== 'all') {
                filtered = filtered.filter(emp => {
                    const matchedTopics = (emp.topics || []).filter(t => {
                        const isMatchTopic = (filterTopic === 'all' || String(t.num) === filterTopic);
                        if (!isMatchTopic) return false;

                        if (filterStatus === 'att1_done') return t.attempt1 !== null && t.attempt1 !== undefined;
                        if (filterStatus === 'att1_pending') return t.attempt1 === null || t.attempt1 === undefined;
                        if (filterStatus === 'att2_done') return t.attempt2 !== null && t.attempt2 !== undefined;
                        if (filterStatus === 'att2_pending') return t.attempt2 === null || t.attempt2 === undefined;

                        return true;
                    });
                    return matchedTopics.length > 0;
                });
            }

            const totalCount = filtered.length;
            const topicCount = data.items[0]?.topics?.length || 4;
            const dynColspan = 3 + topicCount * 4 + 3;
            if (thead) thead.innerHTML = this.buildHeader(topicCount);

            // 3. Paginate (10 items per page)
            const startIndex = (page - 1) * 10;
            const paginated = filtered.slice(startIndex, startIndex + 10);

            if (paginated.length === 0) {
                tbody.innerHTML = `
                    <tr><td colspan="${dynColspan}" style="text-align:center;padding:48px;color:#9ca3af;">
                        <div style="font-size:40px;margin-bottom:12px;">🔍</div>
                        <div style="font-size:16px;font-weight:600;">Маълумот топилмади</div>
                        <div style="font-size:13px;margin-top:4px;">Филтр бўйича мос келувчи ходимлар мавжуд эмас</div>
                    </td></tr>`;
                this.renderPagination(0, page);
                return;
            }

            const B = 'border:1px solid #e5e7eb;';
            const C = `text-align:center;padding:8px 5px;${B}font-size:12px;`;
            const L = `padding:8px 10px;${B}`;

            tbody.innerHTML = paginated.map((emp, idx) => {
                const rowBg = idx % 2 === 0 ? '#ffffff' : '#f8fafc';

                const topicCells = (emp.topics || []).map(t => {
                    const s1 = t.attempt1 !== null && t.attempt1 !== undefined ? `<b>${t.attempt1}%</b>` : '<span style="color:#d1d5db;">—</span>';
                    const s2 = t.attempt2 !== null && t.attempt2 !== undefined ? `<b>${t.attempt2}%</b>` : '<span style="color:#d1d5db;">—</span>';
                    const diff = t.diff !== null && t.diff !== undefined
                        ? `<span style="font-weight:700;color:${t.diff > 0 ? '#16a34a' : t.diff < 0 ? '#dc2626' : '#6b7280'}">${t.diff > 0 ? '+' : ''}${t.diff}%</span>`
                        : '<span style="color:#d1d5db;">—</span>';

                    let holatBg = '#f3f4f6'; let holatC = '#9ca3af'; let holatT = '—';
                    if (t.holat === 'Тугатган') { holatBg = '#dcfce7'; holatC = '#166534'; holatT = '✅ Тугатган'; }
                    else if (t.holat === '1-уринди') { holatBg = '#fef9c3'; holatC = '#854d0e'; holatT = '🔁 1-уринди'; }
                    else if (t.holat === 'Жараёнда') { holatBg = '#dbeafe'; holatC = '#1e40af'; holatT = '🔄 Жараёнда'; }

                    return `
                        <td style="${C}">${s1}</td>
                        <td style="${C}">${s2}</td>
                        <td style="${C}">${diff}</td>
                        <td style="${C}padding:4px;">
                            <span style="background:${holatBg};color:${holatC};padding:3px 7px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap;">${holatT}</span>
                        </td>`;
                }).join('');

                const tot = emp.total || {};
                const ta1 = tot.avg1 !== null && tot.avg1 !== undefined ? `<b style="color:#1e40af;font-size:14px;">${tot.avg1}%</b>` : '<span style="color:#d1d5db;">—</span>';
                const ta2 = tot.avg2 !== null && tot.avg2 !== undefined ? `<b style="color:#166534;font-size:14px;">${tot.avg2}%</b>` : '<span style="color:#d1d5db;">—</span>';
                const tdiff = tot.diff !== null && tot.diff !== undefined
                    ? `<span style="font-weight:800;font-size:14px;color:${tot.diff > 0 ? '#16a34a' : tot.diff < 0 ? '#dc2626' : '#6b7280'}">${tot.diff > 0 ? '+' : ''}${tot.diff}%</span>`
                    : '<span style="color:#d1d5db;">—</span>';

                return `<tr id="emp-row-${emp.id}" style="background:${rowBg};cursor:pointer;transition:background 0.2s;" 
                    onclick="Employees.showDetail('${emp.id}')"
                    onmouseover="this.style.background='#f0fdf4'" 
                    onmouseout="this.style.background='${rowBg}'"
                    title="Ходим маълумотларини ва ўчириш тугмасини кўриш учун босинг">
                    <td style="${C}font-weight:700;color:#9ca3af;">${startIndex + idx + 1}</td>
                    <td style="${L}">
                        <div style="font-weight:700;font-size:13px;color:#111827;display:flex;align-items:center;gap:6px;">
                            <span>👤</span>
                            <span>${emp.name}</span>
                        </div>
                    </td>
                    <td style="${L}font-size:11px;color:#4b5563;line-height:1.3;font-weight:600;">${emp.branch || '—'}</td>
                    ${topicCells}
                    <td style="${C}">${ta1}</td>
                    <td style="${C}">${ta2}</td>
                    <td style="${C}">${tdiff}</td>
                </tr>`;
            }).join('');

            this.renderPagination(totalCount, page);

        } catch (e) {
            console.error('Employees load error:', e);
            const tc2 = 4;
            const colspan2 = 3 + tc2 * 4 + 3;
            const tbody2 = document.getElementById('employeesTableBody');
            if (tbody2) tbody2.innerHTML = `<tr><td colspan="${colspan2}" style="text-align:center;padding:24px;color:#dc2626;font-weight:600;">Хатолик: ${e.message}</td></tr>`;
        }
    },

    renderPagination(total, page) {
        const container = document.getElementById('empPagination');
        if (!container) return;
        const totalPages = Math.ceil(total / 10);
        if (totalPages <= 1) { container.innerHTML = ''; return; }
        let html = '<div style="display:flex;gap:8px;justify-content:center;">';
        for (let p = 1; p <= totalPages; p++) {
            const active = p === page
                ? 'background:linear-gradient(135deg,#15803d,#16a34a);color:#fff;box-shadow:0 4px 12px rgba(22,163,74,0.35);'
                : 'background:#f3f4f6;color:#374151;';
            html += `<button onclick="Dashboard.loadEmployees(${p})" style="${active}border:none;border-radius:8px;padding:8px 16px;cursor:pointer;font-weight:700;font-size:13px;transition:all .2s;">${p}</button>`;
        }
        html += '</div>';
        container.innerHTML = html;
    },

    animateValue(id, start, end, duration) {
        const obj = document.getElementById(id);
        if (!obj) return;
        let startTimestamp = null;
        const step = (ts) => {
            if (!startTimestamp) startTimestamp = ts;
            const prog = Math.min((ts - startTimestamp) / duration, 1);
            obj.textContent = Math.floor(prog * (end - start) + start);
            if (prog < 1) window.requestAnimationFrame(step);
        };
        window.requestAnimationFrame(step);
    },

    debounce(fn, wait) {
        let t;
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
    },

    confirmDeleteEmployee(empId, empName) {
        document.getElementById('deleteEmpModal')?.remove();
        const modal = document.createElement('div');
        modal.id = 'deleteEmpModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.65);backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:#fff;border-radius:20px;padding:36px;max-width:420px;width:90%;box-shadow:0 24px 64px rgba(0,0,0,0.3);text-align:center;">
                <div style="font-size:52px;margin-bottom:14px;">⚠️</div>
                <h2 style="margin:0 0 10px;color:#dc2626;font-size:20px;">Ходимни базадан ўчириш</h2>
                <p style="color:#6b7280;margin:0 0 24px;font-size:15px;line-height:1.6;">
                    <strong style="color:#111827;">${empName}</strong> ходимини маълумотлар базасидан бутунлай ўчирасизми?<br>
                    <span style="color:#dc2626;font-weight:700;font-size:14px;">Ушбу ходимга тегишли барча маълумотлар ва тест тарихи базадан ўчади!</span>
                </p>
                <div style="display:flex;gap:12px;justify-content:center;">
                    <button onclick="document.getElementById('deleteEmpModal').remove()" style="padding:12px 28px;border-radius:10px;border:2px solid #e5e7eb;background:#fff;cursor:pointer;font-size:14px;font-weight:600;color:#374151;">Бекор қилиш</button>
                    <button id="confirmEmpDeleteBtn" onclick="Dashboard.executeDeleteEmployee('${empId}')" style="padding:12px 28px;border-radius:10px;border:none;background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff;cursor:pointer;font-size:14px;font-weight:700;">🗑️ Ҳа, ўчириш</button>
                </div>
            </div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    },

    async executeDeleteEmployee(empId) {
        const btn = document.getElementById('confirmEmpDeleteBtn');
        if (btn) { btn.textContent = "Ўчирилмоқда..."; btn.disabled = true; }
        try {
            await API.deleteEmployee(empId);
            document.getElementById('deleteEmpModal')?.remove();
            Employees.closeModal();
            document.getElementById('emp-row-' + empId)?.remove();
            
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:28px;right:28px;z-index:99999;padding:14px 22px;border-radius:14px;font-weight:700;background:linear-gradient(135deg,#166534,#16a34a);color:#fff;font-size:14px;box-shadow:0 8px 24px rgba(22,163,74,0.4);';
            toast.textContent = "✅ Ходим ва унга тегишли барча маълумотлар базадан ўчирилди!";
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3500);

            this.loadStats();
            this.loadEmployees(this.currentPage);
        } catch (e) {
            document.getElementById('deleteEmpModal')?.remove();
            alert('Хатолик: ' + e.message);
        }
    },

    async exportToExcel() {
        const btn = event?.target?.closest('button');
        const origText = btn?.innerHTML || '';
        if (btn) { btn.innerHTML = '⏳ Юкланмоқда...'; btn.disabled = true; }

        try {
            // Fetch ALL pages
            let allItems = [];
            let page = 1;
            while (true) {
                const data = await API.getDashboardEmployees({ page, search: '' });
                if (!data?.items?.length) break;
                allItems = allItems.concat(data.items);
                if (allItems.length >= (data.total || 0)) break;
                page++;
            }

            const topicCount = allItems[0]?.topics?.length || 4;

            // Colors matching the dashboard
            const H_BG = '#15803d';   // dark green header
            const H_S  = '#22c55e';   // light green subheader
            const D_BG = '#1e3a5f';   // dark blue total header
            const D_S  = '#2563eb';   // blue subheader
            const WHITE = '#ffffff';
            const STRIPE = '#f0fdf4'; // light green row stripe

            // Build header row 1
            let hdr1 = `<tr>
                <th style="background:${H_BG};color:#fff;border:1px solid #166534;padding:10px 8px;font-size:12px;white-space:nowrap;" rowspan="2">№</th>
                <th style="background:${H_BG};color:#fff;border:1px solid #166534;padding:10px 8px;font-size:12px;white-space:nowrap;min-width:160px;" rowspan="2">Ф.И.Ш.</th>
                <th style="background:${H_BG};color:#fff;border:1px solid #166534;padding:10px 8px;font-size:12px;white-space:nowrap;min-width:180px;" rowspan="2">Филиал</th>`;
            for (let i = 1; i <= topicCount; i++) {
                hdr1 += `<th colspan="4" style="background:${H_BG};color:#fff;border:1px solid #166534;padding:10px 8px;font-size:12px;text-align:center;">${i}-Мавзу</th>`;
            }
            hdr1 += `<th colspan="3" style="background:${D_BG};color:#fff;border:1px solid #1e40af;padding:10px 8px;font-size:12px;text-align:center;">Жами якуни</th></tr>`;

            let hdr2 = '<tr>';
            for (let i = 0; i < topicCount; i++) {
                hdr2 += `<th style="background:${H_S};color:#fff;border:1px solid #166534;padding:7px 5px;font-size:11px;text-align:center;">1-уриниш</th>
                          <th style="background:${H_S};color:#fff;border:1px solid #166534;padding:7px 5px;font-size:11px;text-align:center;">2-уриниш</th>
                          <th style="background:${H_S};color:#fff;border:1px solid #166534;padding:7px 5px;font-size:11px;text-align:center;">Фарқ</th>
                          <th style="background:${H_S};color:#fff;border:1px solid #166634;padding:7px 5px;font-size:11px;text-align:center;">Ҳолат</th>`;
            }
            hdr2 += `<th style="background:${D_S};color:#fff;border:1px solid #1e40af;padding:7px 5px;font-size:11px;text-align:center;">1-ур ўртача</th>
                      <th style="background:${D_S};color:#fff;border:1px solid #1e40af;padding:7px 5px;font-size:11px;text-align:center;">2-ур ўртача</th>
                      <th style="background:${D_S};color:#fff;border:1px solid #1e40af;padding:7px 5px;font-size:11px;text-align:center;">Фарқ</th></tr>`;

            // Build data rows
            let rows = '';
            allItems.forEach((emp, idx) => {
                const rowBg = idx % 2 === 0 ? WHITE : STRIPE;
                const C = `border:1px solid #e5e7eb;padding:8px 6px;font-size:12px;text-align:center;background:${rowBg};`;
                const L = `border:1px solid #e5e7eb;padding:8px 8px;font-size:12px;background:${rowBg};`;

                let cells = '';
                (emp.topics || []).forEach(t => {
                    const s1 = t.attempt1 != null ? `${t.attempt1}%` : '—';
                    const s2 = t.attempt2 != null ? `${t.attempt2}%` : '—';
                    const diff = t.diff != null ? `${t.diff > 0 ? '+' : ''}${t.diff}%` : '—';
                    const diffColor = t.diff > 0 ? '#16a34a' : t.diff < 0 ? '#dc2626' : '#6b7280';

                    let holatBg = '#f3f4f6'; let holatC = '#6b7280'; let holatT = '—';
                    if (t.holat === 'Тугатган') { holatBg = '#dcfce7'; holatC = '#166534'; holatT = '✅ Тугатган'; }
                    else if (t.holat === '1-уринди') { holatBg = '#fef9c3'; holatC = '#854d0e'; holatT = '🔁 1-уринди'; }
                    else if (t.holat === 'Жараёнда') { holatBg = '#dbeafe'; holatC = '#1e40af'; holatT = '🔄 Жараёнда'; }

                    cells += `<td style="${C}">${s1}</td><td style="${C}">${s2}</td>
                              <td style="${C}color:${diffColor};font-weight:700;">${diff}</td>
                              <td style="${C}"><span style="background:${holatBg};color:${holatC};padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap;">${holatT}</span></td>`;
                });

                const tot = emp.total || {};
                const ta1 = tot.avg1 != null ? `<b style="color:#1e40af;">${tot.avg1}%</b>` : '—';
                const ta2 = tot.avg2 != null ? `<b style="color:#166534;">${tot.avg2}%</b>` : '—';
                const td  = tot.diff != null ? `<b style="color:${tot.diff > 0 ? '#16a34a' : '#dc2626'};">${tot.diff > 0 ? '+' : ''}${tot.diff}%</b>` : '—';

                rows += `<tr>
                    <td style="${C}font-weight:700;color:#9ca3af;">${idx + 1}</td>
                    <td style="${L}font-weight:700;">${emp.name || ''}</td>
                    <td style="${L}font-size:11px;color:#6b7280;">${emp.branch || ''}</td>
                    ${cells}
                    <td style="${C}">${ta1}</td>
                    <td style="${C}">${ta2}</td>
                    <td style="${C}">${td}</td>
                </tr>`;
            });

            // Full HTML Excel
            const now = new Date().toLocaleDateString('uz-UZ');
            const html = `
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="UTF-8"><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>
<x:Name>Ходимлар рейтинги</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
</x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head>
<body>
<table style="border-collapse:collapse;font-family:Arial,sans-serif;">
<tr><td colspan="${3 + topicCount * 4 + 3}" style="background:#15803d;color:#fff;font-size:16px;font-weight:700;padding:14px 16px;border:none;">
📊 Ходимлар рейтинги — @Eco234_bot — ${now}
</td></tr>
<tr><td colspan="${3 + topicCount * 4 + 3}" style="background:#166534;color:rgba(255,255,255,0.7);font-size:11px;padding:6px 16px;border:none;">
Жами: ${allItems.length} та ходим
</td></tr>
<tr><td colspan="${3 + topicCount * 4 + 3}" style="padding:4px;border:none;"></td></tr>
${hdr1}
${hdr2}
${rows}
</table>
</body></html>`;

            // Download
            const blob = new Blob(['\uFEFF' + html], { type: 'application/vnd.ms-excel;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `hodimlar_reytingi_${new Date().toISOString().slice(0,10)}.xls`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);

            if (btn) { btn.innerHTML = '✅ Юклandi!'; setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 2000); }

        } catch (e) {
            console.error('Excel export error:', e);
            if (btn) { btn.innerHTML = '❌ Хатолик'; setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 2000); }
            alert('Excel юклашда хатолик: ' + e.message);
        }
    }
};


document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('dashboard')) Dashboard.init();
});
