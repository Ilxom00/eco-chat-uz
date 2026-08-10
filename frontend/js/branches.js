const Branches = {
    init() {
        const container = document.getElementById('branches');
        if (!container) return;

        container.innerHTML = `
            <div class="section-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2 style="margin:0;">Filiallar</h2>
                <button class="btn btn-primary" onclick="Branches.showCreateModal()">+ Yangi filial</button>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Filial nomi</th>
                            <th>Xodimlar</th>
                            <th>Tartib</th>
                            <th>Amallar</th>
                        </tr>
                    </thead>
                    <tbody id="branchesList">
                        <tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-secondary)">Yuklanmoqda...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
        this.loadBranches();
    },

    async loadBranches() {
        try {
            const data = await API.getBranches();
            const tbody = document.getElementById('branchesList');

            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-secondary)">Filiallar yo\'q</td></tr>';
                return;
            }

            tbody.innerHTML = data.map((b, idx) => `
                <tr id="branch-row-${b.id}">
                    <td>${idx + 1}</td>
                    <td style="font-weight:600;">${b.name}</td>
                    <td>
                        <span class="badge badge-${b.employee_count > 0 ? 'success' : 'warning'}">
                            ${b.employee_count} xodim
                        </span>
                    </td>
                    <td>${b.sort_order}</td>
                    <td>
                        <button 
                            onclick="Branches.confirmDelete('${b.id}', '${b.name.replace(/'/g,"\\'")}', ${b.employee_count})"
                            style="
                                background: linear-gradient(135deg, #dc2626, #b91c1c);
                                color: white; border: none; border-radius: 7px;
                                padding: 7px 14px; cursor: pointer; font-size: 13px;
                                font-weight: 600; transition: all 0.2s;
                            "
                            onmouseover="this.style.transform='scale(1.05)'"
                            onmouseout="this.style.transform='scale(1)'"
                        >🗑️ O'chirish</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error(e);
            const tbody = document.getElementById('branchesList');
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger);padding:20px">Xato: ${e.message}</td></tr>`;
        }
    },

    confirmDelete(branchId, branchName, empCount) {
        const existing = document.getElementById('deleteBranchModal');
        if (existing) existing.remove();

        const warning = empCount > 0
            ? `<p style="color:var(--danger,#dc2626);font-weight:600;margin-top:8px;">⚠️ ${empCount} ta xodim bu filialdan chiqariladi (o'chirilmaydi)!</p>`
            : '';

        const modal = document.createElement('div');
        modal.id = 'deleteBranchModal';
        modal.style.cssText = `
            position:fixed;inset:0;z-index:9999;
            background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);
            display:flex;align-items:center;justify-content:center;
        `;
        modal.innerHTML = `
            <div style="background:var(--bg-card,#fff);border-radius:16px;padding:32px;max-width:440px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                <div style="text-align:center;margin-bottom:20px;">
                    <div style="font-size:48px;margin-bottom:12px;">⚠️</div>
                    <h2 style="margin:0 0 8px 0;color:var(--danger,#dc2626);">Filialni o'chirish</h2>
                    <p style="color:var(--text-secondary);margin:0;font-size:15px;">
                        <strong>"${branchName}"</strong> filialni o'chirasizmi?<br>
                        Filial ma'lumotlari bazadan to'liq o'chadi.
                    </p>
                    ${warning}
                </div>
                <div style="display:flex;gap:12px;justify-content:center;">
                    <button onclick="document.getElementById('deleteBranchModal').remove()"
                        style="padding:12px 24px;border-radius:8px;border:2px solid var(--border,#e5e7eb);background:transparent;cursor:pointer;font-size:15px;font-weight:600;color:var(--text-secondary);">
                        Bekor
                    </button>
                    <button id="confirmBranchDeleteBtn" onclick="Branches.executeDelete('${branchId}')"
                        style="padding:12px 24px;border-radius:8px;border:none;background:linear-gradient(135deg,#dc2626,#b91c1c);color:white;cursor:pointer;font-size:15px;font-weight:600;">
                        🗑️ Ha, o'chirish
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    },

    async executeDelete(branchId) {
        const btn = document.getElementById('confirmBranchDeleteBtn');
        if (btn) { btn.textContent = "O'chirilmoqda..."; btn.disabled = true; }
        try {
            await API.deleteBranch(branchId);
            document.getElementById('deleteBranchModal')?.remove();
            Branches.showToast("✅ Filial muvaffaqiyatli o'chirildi!", 'success');
            await this.loadBranches();
        } catch (e) {
            document.getElementById('deleteBranchModal')?.remove();
            Branches.showToast("❌ Xato: " + e.message, 'error');
        }
    },

    showToast(msg, type) {
        const t = document.createElement('div');
        t.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:99999;padding:14px 20px;border-radius:12px;font-weight:600;background:${type==='success'?'#16a34a':'#dc2626'};color:white;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,0.2);`;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 3000);
    },

    showCreateModal() {
        const existing = document.getElementById('createBranchModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'createBranchModal';
        modal.style.cssText = `position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;`;
        modal.innerHTML = `
            <div style="background:var(--bg-card,#fff);border-radius:16px;padding:32px;max-width:440px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                <h2 style="margin:0 0 20px 0;">+ Yangi filial</h2>
                <div style="margin-bottom:20px;">
                    <label style="display:block;margin-bottom:6px;font-weight:600;">Filial nomi</label>
                    <input id="branchNameInput" type="text" placeholder="Masalan: Toshkent shahri" style="width:100%;padding:10px 14px;border-radius:8px;border:2px solid var(--border,#e5e7eb);font-size:15px;box-sizing:border-box;">
                </div>
                <div style="display:flex;gap:12px;justify-content:flex-end;">
                    <button onclick="document.getElementById('createBranchModal').remove()" style="padding:10px 20px;border-radius:8px;border:2px solid var(--border,#e5e7eb);background:transparent;cursor:pointer;font-size:14px;font-weight:600;">Bekor</button>
                    <button onclick="Branches.submitCreate()" style="padding:10px 20px;border-radius:8px;border:none;background:var(--primary,#166534);color:white;cursor:pointer;font-size:14px;font-weight:600;">Saqlash</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
        document.getElementById('branchNameInput').focus();
    },

    async submitCreate() {
        const name = document.getElementById('branchNameInput').value.trim();
        if (!name) { alert("Filial nomini kiriting!"); return; }
        try {
            await API.createBranch({ name });
            document.getElementById('createBranchModal').remove();
            Branches.showToast("✅ Filial yaratildi!", 'success');
            await this.loadBranches();
        } catch (e) {
            alert("Xato: " + e.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.querySelector('[data-target="branches"]');
    if (btn) btn.addEventListener('click', () => Branches.init());
});
