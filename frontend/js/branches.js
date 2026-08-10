const Branches = {
    init() {
        const container = document.getElementById('branches');
        if (!container) return;

        container.innerHTML = `
            <div class="section-header" style="display:flex; justify-content:space-between; margin-bottom:20px;">
                <h2>Филиаллар</h2>
                <button class="btn btn-primary" onclick="Branches.showCreateModal()">+ Янги филиал</button>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>№</th>
                            <th>Номи</th>
                            <th>Тартиб</th>
                            <th>Амаллар</th>
                        </tr>
                    </thead>
                    <tbody id="branchesList">
                    </tbody>
                </table>
            </div>
        `;
        this.loadBranches();
    },

    async loadBranches() {
        try {
            // MOCK
            const data = [
                { id: 1, name: 'Тошкент шаҳар бошқармаси', sort_order: 1 },
                { id: 2, name: 'Самарқанд вилояти бошқармаси', sort_order: 2 }
            ];
            
            document.getElementById('branchesList').innerHTML = data.map((b, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${b.name}</td>
                    <td>${b.sort_order}</td>
                    <td>
                        <button class="btn btn-outline input-sm">Таҳрирлаш</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error(e);
        }
    },
    
    showCreateModal() {
        alert('Create branch modal');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('[data-target="branches"]').addEventListener('click', () => {
        Branches.init();
    });
});
