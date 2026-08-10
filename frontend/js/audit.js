const Audit = {
    init() {
        const container = document.getElementById('audit');
        if (!container) return;

        container.innerHTML = `
            <div class="section-header" style="margin-bottom:20px;">
                <h2>Audit Log</h2>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Сана ва вақт</th>
                            <th>Фойдаланувчи</th>
                            <th>Ҳаракат</th>
                            <th>Тафсилотлар</th>
                        </tr>
                    </thead>
                    <tbody id="auditList">
                        <!-- MOCK -->
                        <tr>
                            <td>2023-10-27 14:32:00</td>
                            <td>Super Admin</td>
                            <td><span class="badge badge-success">CREATE_TOPIC</span></td>
                            <td>"Экология" мавзуси яратилди</td>
                        </tr>
                        <tr>
                            <td>2023-10-27 14:35:12</td>
                            <td>Super Admin</td>
                            <td><span class="badge badge-warning">IMPORT_QUESTIONS</span></td>
                            <td>45 та савол импорт қилинди</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('[data-target="audit"]').addEventListener('click', () => {
        Audit.init();
    });
});
