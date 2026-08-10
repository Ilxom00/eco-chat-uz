const Reports = {
    init() {
        const container = document.getElementById('reports');
        if (!container) return;

        container.innerHTML = `
            <div class="section-header" style="margin-bottom:20px;">
                <h2>Ҳисоботлар</h2>
            </div>
            <div class="kpi-grid" style="margin-bottom:24px;">
                <div class="kpi-card" style="display:block; text-align:center; cursor:pointer;" onclick="Reports.download('general')">
                    <div class="kpi-icon" style="margin:0 auto 12px auto;">📊</div>
                    <h3>Умумий ҳисобот</h3>
                    <button class="btn btn-primary mt-4">Excel юклаш</button>
                </div>
                <div class="kpi-card" style="display:block; text-align:center; cursor:pointer;" onclick="Reports.download('topic')">
                    <div class="kpi-icon" style="margin:0 auto 12px auto;">📝</div>
                    <h3>Мавзу бўйича</h3>
                    <button class="btn btn-primary mt-4">Excel юклаш</button>
                </div>
                <div class="kpi-card" style="display:block; text-align:center; cursor:pointer;" onclick="Reports.download('employee')">
                    <div class="kpi-icon" style="margin:0 auto 12px auto;">👥</div>
                    <h3>Ходим бўйича</h3>
                    <button class="btn btn-primary mt-4">Excel юклаш</button>
                </div>
            </div>
            <div class="table-container">
                <h3>Фильтрлар</h3>
                <div class="form-row mt-4">
                    <div class="form-group">
                        <label>Филиал</label>
                        <select class="form-control"><option>Барчаси</option></select>
                    </div>
                    <div class="form-group">
                        <label>Мавзу</label>
                        <select class="form-control"><option>Барчаси</option></select>
                    </div>
                    <div class="form-group">
                        <label>Сана</label>
                        <input type="date" class="form-control">
                    </div>
                </div>
            </div>
        `;
    },

    download(type) {
        alert(`Downloading ${type} report... (API call to backend)`);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('[data-target="reports"]').addEventListener('click', () => {
        Reports.init();
    });
});
