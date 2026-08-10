const Topics = {
    init() {
        this.loadTopics();
    },

    async loadTopics() {
        const container = document.getElementById('topicsList');
        if (!container) return;
        container.innerHTML = '<div style="padding:20px;color:var(--text-secondary)">Yuklanmoqda...</div>';

        try {
            const topics = await API.getTopics();

            if (!topics || topics.length === 0) {
                container.innerHTML = '<div style="padding:20px;color:var(--text-secondary)">Mavzular yo\'q. Yangi mavzu qo\'shing.</div>';
                return;
            }

            container.innerHTML = topics.map(t => `
                <div class="kpi-card topic-item" id="topic-${t.id}" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="flex:1; cursor:pointer;" onclick="Questions.loadForTopic('${t.id}', '${t.short_name}')">
                        <h3 style="margin:0 0 6px 0;">${t.short_name}</h3>
                        <div style="font-size:14px; color:var(--text-secondary);">${t.full_name}</div>
                    </div>
                    <div style="display:flex; align-items:center; gap:12px; flex-shrink:0;">
                        <div class="badge badge-success">${t.q_count} савол</div>
                        <button 
                            onclick="Topics.confirmDelete('${t.id}', '${t.short_name}')" 
                            style="
                                background: linear-gradient(135deg, #dc2626, #b91c1c);
                                color: white;
                                border: none;
                                border-radius: 8px;
                                padding: 8px 16px;
                                cursor: pointer;
                                font-size: 13px;
                                font-weight: 600;
                                display: flex;
                                align-items: center;
                                gap: 6px;
                                transition: all 0.2s;
                            "
                            onmouseover="this.style.transform='scale(1.05)'"
                            onmouseout="this.style.transform='scale(1)'"
                        >
                            🗑️ O'chirish
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = `<div style="padding:20px;color:var(--danger)">Xato: ${e.message}</div>`;
            console.error(e);
        }
    },

    confirmDelete(topicId, topicName) {
        // Create confirmation modal
        const existing = document.getElementById('deleteTopicModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'deleteTopicModal';
        modal.style.cssText = `
            position: fixed; inset: 0; z-index: 9999;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center;
        `;
        modal.innerHTML = `
            <div style="
                background: var(--bg-card, #fff);
                border-radius: 16px;
                padding: 32px;
                max-width: 440px;
                width: 90%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideIn 0.2s ease;
            ">
                <div style="text-align:center; margin-bottom:20px;">
                    <div style="font-size:48px; margin-bottom:12px;">⚠️</div>
                    <h2 style="margin:0 0 8px 0; color: var(--danger, #dc2626);">O'chirishni tasdiqlang</h2>
                    <p style="color:var(--text-secondary); margin:0; font-size:15px;">
                        <strong>"${topicName}"</strong> mavzusini o'chirasizmi?<br>
                        <span style="color:var(--danger, #dc2626); font-weight:600;">
                            Barcha savollar, natijalar va bog'liq ma'lumotlar ham o'chadi!
                        </span>
                    </p>
                </div>
                <div style="display:flex; gap:12px; justify-content:center;">
                    <button 
                        onclick="document.getElementById('deleteTopicModal').remove()"
                        style="
                            padding: 12px 24px; border-radius: 8px; border: 2px solid var(--border, #e5e7eb);
                            background: transparent; cursor: pointer; font-size: 15px; font-weight: 600;
                            color: var(--text-secondary); transition: all 0.2s;
                        "
                    >Bekor qilish</button>
                    <button 
                        id="confirmDeleteBtn"
                        onclick="Topics.executDelete('${topicId}')"
                        style="
                            padding: 12px 24px; border-radius: 8px; border: none;
                            background: linear-gradient(135deg, #dc2626, #b91c1c);
                            color: white; cursor: pointer; font-size: 15px; font-weight: 600;
                            transition: all 0.2s;
                        "
                    >🗑️ Ha, o'chirish</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    },

    async executDelete(topicId) {
        const btn = document.getElementById('confirmDeleteBtn');
        if (btn) { btn.textContent = 'O\'chirilmoqda...'; btn.disabled = true; }

        try {
            await API.deleteTopic(topicId);

            // Close modal
            const modal = document.getElementById('deleteTopicModal');
            if (modal) modal.remove();

            // Show success toast
            Topics.showToast('✅ Mavzu muvaffaqiyatli o\'chirildi!', 'success');

            // Reload topics list
            await this.loadTopics();
        } catch (e) {
            const modal = document.getElementById('deleteTopicModal');
            if (modal) modal.remove();
            Topics.showToast(`❌ Xato: ${e.message}`, 'error');
            console.error(e);
        }
    },

    showToast(msg, type) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 24px; right: 24px; z-index: 99999;
            padding: 14px 20px; border-radius: 12px; font-weight: 600;
            background: ${type === 'success' ? '#16a34a' : '#dc2626'};
            color: white; font-size: 14px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },

    showCreateModal() {
        const existing = document.getElementById('createTopicModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'createTopicModal';
        modal.style.cssText = `
            position: fixed; inset: 0; z-index: 9999;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center;
        `;
        modal.innerHTML = `
            <div style="
                background: var(--bg-card, #fff);
                border-radius: 16px;
                padding: 32px;
                max-width: 480px;
                width: 90%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            ">
                <h2 style="margin:0 0 20px 0;">+ Yangi mavzu</h2>
                <div style="margin-bottom:16px;">
                    <label style="display:block; margin-bottom:6px; font-weight:600;">Qisqa nomi</label>
                    <input id="topicShortName" type="text" placeholder="Masalan: Ekologiya" style="
                        width:100%; padding:10px 14px; border-radius:8px;
                        border:2px solid var(--border, #e5e7eb); font-size:15px; box-sizing:border-box;
                    ">
                </div>
                <div style="margin-bottom:24px;">
                    <label style="display:block; margin-bottom:6px; font-weight:600;">To'liq nomi</label>
                    <input id="topicFullName" type="text" placeholder="Masalan: Ekologiya va atrof-muhit muhofazasi" style="
                        width:100%; padding:10px 14px; border-radius:8px;
                        border:2px solid var(--border, #e5e7eb); font-size:15px; box-sizing:border-box;
                    ">
                </div>
                <div style="display:flex; gap:12px; justify-content:flex-end;">
                    <button onclick="document.getElementById('createTopicModal').remove()"
                        style="padding:10px 20px; border-radius:8px; border:2px solid var(--border, #e5e7eb);
                        background:transparent; cursor:pointer; font-size:14px; font-weight:600;">
                        Bekor
                    </button>
                    <button onclick="Topics.submitCreate()"
                        style="padding:10px 20px; border-radius:8px; border:none;
                        background:var(--primary, #166534); color:white; cursor:pointer; font-size:14px; font-weight:600;">
                        Saqlash
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        document.getElementById('topicShortName').focus();
    },

    async submitCreate() {
        const short = document.getElementById('topicShortName').value.trim();
        const full = document.getElementById('topicFullName').value.trim();
        if (!short || !full) { alert('Iltimos, ikkala maydonni ham to\'ldiring!'); return; }

        try {
            await API.createTopic({ short_name: short, full_name: full });
            document.getElementById('createTopicModal').remove();
            Topics.showToast('✅ Mavzu yaratildi!', 'success');
            await this.loadTopics();
        } catch (e) {
            alert('Xato: ' + e.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.querySelector('[data-target="topics"]');
    if (btn) {
        btn.addEventListener('click', () => Topics.init());
    }
});
