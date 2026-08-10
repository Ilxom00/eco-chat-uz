const Dashboard = {
    currentPage: 1,

    init() {
        this.loadStats();
        this.loadEmployees(1);

        const searchInput = document.getElementById('empSearch');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => this.loadEmployees(1), 500));
        }
    },

    async loadStats() {
        try {
            const stats = await API.getDashboardStats();
            this.animateValue('kpi-total-employees', 0, stats.totalEmployees || 0, 1000);
            this.animateValue('kpi-started', 0, stats.started || 0, 1000);
            this.animateValue('kpi-completed', 0, stats.completed || 0, 1000);
            const active = document.getElementById('kpi-active');
            if (active) active.textContent = stats.active || 0;
            const avg1 = document.getElementById('kpi-avg1');
            if (avg1) avg1.textContent = (stats.avg1 || 0) + '%';
            const avg2 = document.getElementById('kpi-avg2');
            if (avg2) avg2.textContent = (stats.avg2 || 0) + '%';
            const growth = document.getElementById('kpi-growth');
            if (growth) growth.textContent = '+' + (stats.growth || 0) + '%';
            this.animateValue('kpi-total-tests', 0, stats.totalTests || 0, 1000);
        } catch (e) {
            console.error('Failed to load stats', e);
        }
    },

    buildHeader(topicCount) {
        // Green header style
        const GR = 'background:#16a34a;color:#fff;text-align:center;padding:8px 4px;border:1px solid #15803d;white-space:nowrap;font-size:12px;';
        const GR2 = 'background:#22c55e;color:#fff;text-align:center;padding:6px 4px;border:1px solid #15803d;white-space:nowrap;font-size:11px;';

        let row1 = `<tr>
            <th rowspan="2" style="${GR}">№</th>
            <th rowspan="2" style="${GR}min-width:140px;">Ф.И.Ш.</th>
            <th rowspan="2" style="${GR}min-width:160px;">Филиал</th>`;

        let row2 = '<tr>';

        for (let i = 1; i <= topicCount; i++) {
            row1 += `<th colspan="4" style="${GR}">${i} Мавзу</th>`;
            row2 += `
                <th style="${GR2}">1-уриниш</th>
                <th style="${GR2}">2-уриниш</th>
                <th style="${GR2}">Фарқ</th>
                <th style="${GR2}">Ҳолат</th>`;
        }

        // Jami yakuni
        row1 += `<th colspan="3" style="${GR}">Жами якуни</th>`;
        row2 += `
            <th style="${GR2}">1-уринишлар</th>
            <th style="${GR2}">2-уринишлар</th>
            <th style="${GR2}">Фарқ</th>`;

        row1 += '</tr>';
        row2 += '</tr>';

        // Delete col header
        row1 += '';

        return row1 + row2;
    },

    async loadEmployees(page = 1) {
        this.currentPage = page;
        try {
            const search = document.getElementById('empSearch')?.value || '';
            const data = await API.getDashboardEmployees({ page, search });

            const thead = document.getElementById('ratingTableHead');
            const tbody = document.getElementById('employeesTableBody');

            if (!data || !data.items || data.items.length === 0) {
                if (thead) thead.innerHTML = this.buildHeader(4);
                if (tbody) tbody.innerHTML = '<tr><td colspan="20" style="text-align:center;padding:24px;color:#888">Маълумот йўқ</td></tr>';
                return;
            }

            const topicCount = data.items[0]?.topics?.length || 4;
            if (thead) thead.innerHTML = this.buildHeader(topicCount);

            const CELL = 'text-align:center;padding:6px 4px;border:1px solid #e5e7eb;';
            const CELL_L = 'padding:6px 8px;border:1px solid #e5e7eb;';

            tbody.innerHTML = data.items.map((emp, idx) => {
                const topicCells = (emp.topics || []).map(t => {
                    const s1 = t.attempt1 !== null && t.attempt1 !== undefined ? t.attempt1 + '%' : '—';
                    const s2 = t.attempt2 !== null && t.attempt2 !== undefined ? t.attempt2 + '%' : '—';
                    const diff = t.diff !== null && t.diff !== undefined
                        ? `<span style="color:${t.diff > 0 ? '#16a34a' : t.diff < 0 ? '#dc2626' : '#6b7280'}">${t.diff > 0 ? '+' : ''}${t.diff}%</span>`
                        : '—';
                    const holat = t.holat || '—';
                    const holatColor = holat === 'Тугатган' ? '#16a34a' : holat === '1-уринди' ? '#d97706' : holat === 'Жараёнда' ? '#3b82f6' : '#9ca3af';
                    return `
                        <td style="${CELL}">${s1}</td>
                        <td style="${CELL}">${s2}</td>
                        <td style="${CELL}">${diff}</td>
                        <td style="${CELL}font-size:11px;color:${holatColor};font-weight:600;">${holat}</td>`;
                }).join('');

                const tot = emp.total || {};
                const ta1 = tot.avg1 !== null && tot.avg1 !== undefined ? tot.avg1 + '%' : '—';
                const ta2 = tot.avg2 !== null && tot.avg2 !== undefined ? tot.avg2 + '%' : '—';
                const tdiff = tot.diff !== null && tot.diff !== undefined
                    ? `<span style="color:${tot.diff > 0 ? '#16a34a' : tot.diff < 0 ? '#dc2626' : '#6b7280'}">${tot.diff > 0 ? '+' : ''}${tot.diff}%</span>`
                    : '—';

                const rowBg = idx % 2 === 0 ? '#fff' : '#f9fafb';

                return `<tr id="emp-row-${emp.id}" style="background:${rowBg};">
                    <td style="${CELL}">${(page-1)*10 + idx + 1}</td>
                    <td style="${CELL_L}cursor:pointer;font-weight:500;" onclick="Employees.showDetail('${emp.id}')">${emp.name}</td>
                    <td style="${CELL_L}font-size:12px;color:#6b7280;">${emp.branch}</td>
                    ${topicCells}
                    <td style="${CELL}font-weight:600;">${ta1}</td>
                    <td style="${CELL}font-weight:600;">${ta2}</td>
                    <td style="${CELL}font-weight:600;">${tdiff}</td>
                    <td style="${CELL}">
                        <button
                            onclick="Dashboard.confirmDeleteEmployee('${emp.id}', '${(emp.name||'').replace(/'/g,"\\'")}')"
                            style="background:linear-gradient(135deg,#dc2626,#b91c1c);color:white;border:none;border-radius:6px;padding:4px 10px;cursor:pointer;font-size:12px;"
                            title="O'chirish"
                        >🗑️</button>
                    </td>
                </tr>`;
            }).join('');

            // Pagination
            this.renderPagination(data.total, page);

        } catch (e) {
            console.error(e);
            const tbody = document.getElementById('employeesTableBody');
            if (tbody) tbody.innerHTML = `<tr><td colspan="20" style="color:var(--danger);padding:20px">Xato: ${e.message}</td></tr>`;
        }
    },

    renderPagination(total, page) {
        const container = document.getElementById('empPagination');
        if (!container) return;
        const totalPages = Math.ceil(total / 10);
        if (totalPages <= 1) { container.innerHTML = ''; return; }

        let html = '<div style="display:flex;gap:8px;justify-content:center;margin-top:16px;">';
        for (let p = 1; p <= totalPages; p++) {
            const active = p === page ? 'background:var(--primary,#166534);color:white;' : 'background:#f3f4f6;color:#374151;';
            html += `<button onclick="Dashboard.loadEmployees(${p})" style="${active}border:none;border-radius:6px;padding:8px 14px;cursor:pointer;font-weight:600;">${p}</button>`;
        }
        html += '</div>';
        container.innerHTML = html;
    },

    animateValue(id, start, end, duration) {
        const obj = document.getElementById(id);
        if (!obj) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) window.requestAnimationFrame(step);
        };
        window.requestAnimationFrame(step);
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => { clearTimeout(timeout); func(...args); };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    confirmDeleteEmployee(empId, empName) {
        const existing = document.getElementById('deleteEmpModal');
        if (existing) existing.remove();
        const modal = document.createElement('div');
        modal.id = 'deleteEmpModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:var(--bg-card,#fff);border-radius:16px;padding:32px;max-width:440px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                <div style="text-align:center;margin-bottom:20px;">
                    <div style="font-size:48px;margin-bottom:12px;">⚠️</div>
                    <h2 style="margin:0 0 8px 0;color:var(--danger,#dc2626);">Xodimni o'chirish</h2>
                    <p style="color:var(--text-secondary);margin:0;font-size:15px;">
                        <strong>${empName}</strong> xodimini o'chirasizmi?<br>
                        <span style="color:var(--danger,#dc2626);font-weight:600;">Barcha test natijalari va tarix ham o'chadi!</span>
                    </p>
                </div>
                <div style="display:flex;gap:12px;justify-content:center;">
                    <button onclick="document.getElementById('deleteEmpModal').remove()" style="padding:12px 24px;border-radius:8px;border:2px solid var(--border,#e5e7eb);background:transparent;cursor:pointer;font-size:15px;font-weight:600;">Bekor</button>
                    <button id="confirmEmpDeleteBtn" onclick="Dashboard.executeDeleteEmployee('${empId}')" style="padding:12px 24px;border-radius:8px;border:none;background:linear-gradient(135deg,#dc2626,#b91c1c);color:white;cursor:pointer;font-size:15px;font-weight:600;">🗑️ Ha, o'chirish</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    },

    async executeDeleteEmployee(empId) {
        const btn = document.getElementById('confirmEmpDeleteBtn');
        if (btn) { btn.textContent = "O'chirilmoqda..."; btn.disabled = true; }
        try {
            await API.deleteEmployee(empId);
            document.getElementById('deleteEmpModal')?.remove();
            const row = document.getElementById('emp-row-' + empId);
            if (row) row.remove();
            const t = document.createElement('div');
            t.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;padding:14px 20px;border-radius:12px;font-weight:600;background:#16a34a;color:white;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,0.2);';
            t.textContent = "✅ Xodim o'chirildi!";
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 3000);
        } catch (e) {
            document.getElementById('deleteEmpModal')?.remove();
            alert('Xato: ' + e.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('dashboard')) {
        Dashboard.init();
    }
});
