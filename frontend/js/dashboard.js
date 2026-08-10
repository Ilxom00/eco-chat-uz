const Dashboard = {
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
            document.getElementById('kpi-active').textContent = stats.active || 0;
            document.getElementById('kpi-avg1').textContent = (stats.avg1 || 0) + '%';
            document.getElementById('kpi-avg2').textContent = (stats.avg2 || 0) + '%';
            document.getElementById('kpi-growth').textContent = '+' + (stats.growth || 0) + '%';
            this.animateValue('kpi-total-tests', 0, stats.totalTests || 0, 1000);
        } catch (e) {
            console.error('Failed to load stats', e);
        }
    },

    async loadEmployees(page = 1) {
        try {
            const search = document.getElementById('empSearch')?.value || '';
            const data = await API.getDashboardEmployees({ page, search });

            const tbody = document.getElementById('employeesTableBody');
            if (!data || !data.items || data.items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#888">Ma\'lumot yo\'q</td></tr>';
                return;
            }
            tbody.innerHTML = data.items.map((emp, idx) => `
                <tr id="emp-row-${emp.id}">
                    <td>${(page-1)*10 + idx + 1}</td>
                    <td style="cursor:pointer;font-weight:500;" onclick="Employees.showDetail('${emp.id}')">${emp.name}</td>
                    <td>${emp.branch}</td>
                    <td>${emp.topic}</td>
                    <td>${emp.attempt1}%</td>
                    <td>${emp.attempt2 ? emp.attempt2+'%' : '-'}</td>
                    <td style="color: ${emp.diff > 0 ? 'var(--success)' : (emp.diff < 0 ? 'var(--danger)' : '')}">${emp.diff > 0 ? '+'+emp.diff : emp.diff}%</td>
                    <td>
                        <span class="badge ${emp.status === 'completed' ? 'badge-success' : 'badge-warning'}">
                            ${emp.status === 'completed' ? 'Тугатган' : 'Жараёнда'}
                        </span>
                    </td>
                    <td>
                        <button
                            onclick="Dashboard.confirmDeleteEmployee('${emp.id}', '${(emp.name||'').replace(/'/g,"\\'")}')"
                            style="background:linear-gradient(135deg,#dc2626,#b91c1c);color:white;border:none;border-radius:7px;padding:6px 12px;cursor:pointer;font-size:12px;font-weight:600;transition:all 0.2s;"
                            onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'"
                        >🗑️</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error(e);
        }
    },

    animateValue(id, start, end, duration) {
        const obj = document.getElementById(id);
        if (!obj) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
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
            // Show toast
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
