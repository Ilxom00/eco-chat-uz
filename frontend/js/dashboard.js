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
                <tr onclick="Employees.showDetail(${emp.id})">
                    <td>${(page-1)*10 + idx + 1}</td>
                    <td>${emp.name}</td>
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
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('dashboard')) {
        Dashboard.init();
    }
});
