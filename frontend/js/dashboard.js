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
            // const stats = await API.getDashboardStats();
            // MOCK DATA
            const stats = {
                totalEmployees: 1250,
                started: 850,
                completed: 620,
                active: 45,
                avg1: 65,
                avg2: 82,
                growth: 17,
                totalTests: 1470
            };

            this.animateValue('kpi-total-employees', 0, stats.totalEmployees, 1000);
            this.animateValue('kpi-started', 0, stats.started, 1000);
            this.animateValue('kpi-completed', 0, stats.completed, 1000);
            document.getElementById('kpi-active').textContent = stats.active; // Live updating
            document.getElementById('kpi-avg1').textContent = stats.avg1 + '%';
            document.getElementById('kpi-avg2').textContent = stats.avg2 + '%';
            document.getElementById('kpi-growth').textContent = '+' + stats.growth + '%';
            this.animateValue('kpi-total-tests', 0, stats.totalTests, 1000);
        } catch (e) {
            console.error('Failed to load stats', e);
        }
    },

    async loadEmployees(page = 1) {
        try {
            const search = document.getElementById('empSearch')?.value || '';
            // const data = await API.getDashboardEmployees({ page, search });
            // MOCK DATA
            const data = {
                items: [
                    { id: 1, name: 'Абдуллаев Алишер', branch: 'Тошкент ш.', topic: 'Экология асослари', attempt1: 65, attempt2: 85, diff: 20, status: 'completed' },
                    { id: 2, name: 'Ботиров Бекзод', branch: 'Самарқанд вил.', topic: 'Чиқиндилар', attempt1: 40, attempt2: 0, diff: 0, status: 'in-progress' },
                ],
                total: 2,
                pages: 1
            };

            const tbody = document.getElementById('employeesTableBody');
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
            
            // Pagination logic here
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
