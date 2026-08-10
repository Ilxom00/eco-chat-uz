const Employees = {
    showDetail(id) {
        const modal = document.getElementById('employeeModal');
        const body = document.getElementById('employeeModalBody');
        
        // MOCK DATA
        const emp = {
            name: 'Абдуллаев Алишер',
            branch: 'Тошкент шаҳар бошқармаси',
            position: 'Етакчи мутахассис',
            pinfl: '31234567890123'
        };

        body.innerHTML = `
            <div style="display:flex; gap:20px; margin-bottom:24px;">
                <div class="avatar" style="width:80px; height:80px; font-size:24px;">АА</div>
                <div>
                    <h2>${emp.name}</h2>
                    <p style="color:var(--text-secondary); margin-top:8px;">${emp.branch}</p>
                    <p style="color:var(--text-secondary);">${emp.position} | ПИНФЛ: ${emp.pinfl}</p>
                </div>
            </div>
            <h3>Тест натижалари</h3>
            <table class="data-table mt-4">
                <thead>
                    <tr>
                        <th>Мавзу</th>
                        <th>1-уриниш</th>
                        <th>2-уриниш</th>
                        <th>Ҳолат</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Экология асослари</td>
                        <td>65% (10/15)</td>
                        <td>85% (13/15)</td>
                        <td><span class="badge badge-success">Тугатган</span></td>
                    </tr>
                </tbody>
            </table>
            <div style="margin-top:24px;">
                <button class="btn btn-outline" onclick="Employees.showAudit(${id})">15 та савол аудитини кўриш</button>
            </div>
        `;

        modal.style.display = 'flex';

        modal.querySelector('.close-modal').onclick = () => {
            modal.style.display = 'none';
        };
    },

    showAudit(id) {
        alert('Audit view expanding: shows exact questions, selected answers vs correct answers.');
    }
};
