const Topics = {
    init() {
        this.loadTopics();
    },

    async loadTopics() {
        const container = document.getElementById('topicsList');
        if (!container) return;
        container.innerHTML = '<div style="padding:20px;color:var(--text-secondary)">Юкланмоқда...</div>';

        try {
            const topics = await API.getTopics();

            if (!topics || topics.length === 0) {
                container.innerHTML = '<div style="padding:20px;color:var(--text-secondary)">Мавзулар йўқ. Янги мавзу қўшинг.</div>';
                return;
            }

            container.innerHTML = topics.map((t, i) => `
                <div class="kpi-card topic-item" id="topic-${t.id}" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-left:6px solid #16a34a; background:#fff; padding:16px 20px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.05);">
                    <div style="flex:1; cursor:pointer;" onclick="Questions.loadForTopic('${t.id}', '${(t.short_name || '').replace(/'/g, "\\'")}')">
                        <div style="font-size:11px;font-weight:700;color:#166534;letter-spacing:1px;margin-bottom:4px;">${i + 1}-МАВЗУ</div>
                        <h3 style="margin:0 0 4px 0;font-size:16px;color:#111827;">${t.short_name}</h3>
                        <div style="font-size:13px; color:#6b7280; font-weight:500;">${t.full_name}</div>
                    </div>
                    <div style="display:flex; align-items:center; gap:16px; flex-shrink:0;">
                        <span style="background:#dcfce7;color:#166534;padding:6px 14px;border-radius:20px;font-size:13px;font-weight:700;">
                            ${t.q_count} та савол
                        </span>
                        <button 
                            onclick="Topics.confirmDelete('${t.id}', '${(t.short_name || '').replace(/'/g, "\\'")}')" 
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
                                transition: transform 0.15s;
                            "
                            onmouseover="this.style.transform='scale(1.04)'"
                            onmouseout="this.style.transform='scale(1)'"
                        >
                            🗑️ Ўчириш
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = `<div style="padding:20px;color:var(--danger)">Хатолик: ${e.message}</div>`;
            console.error(e);
        }
    },

    confirmDelete(topicId, topicName) {
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
                background: #fff;
                border-radius: 16px;
                padding: 32px;
                max-width: 440px;
                width: 90%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
            ">
                <div style="font-size:48px; margin-bottom:12px;">⚠️</div>
                <h2 style="margin:0 0 8px 0; color: #dc2626;">Ўчиришни тасдиқланг</h2>
                <p style="color:#6b7280; margin:0 0 20px; font-size:15px; line-height:1.5;">
                    <strong style="color:#111827;">"${topicName}"</strong> мавзусини ўчирасизми?<br>
                    <span style="color:#dc2626; font-weight:600;">
                        Барча саволлар, натижалар ва боғлиқ маълумотлар ҳам ўчади!
                    </span>
                </p>
                <div style="display:flex; gap:12px; justify-content:center;">
                    <button 
                        onclick="document.getElementById('deleteTopicModal').remove()"
                        style="
                            padding: 12px 24px; border-radius: 8px; border: 2px solid #e5e7eb;
                            background: transparent; cursor: pointer; font-size: 15px; font-weight: 600;
                            color: #374151;
                        "
                    >Бекор қилиш</button>
                    <button 
                        id="confirmDeleteBtn"
                        onclick="Topics.executDelete('${topicId}')"
                        style="
                            padding: 12px 24px; border-radius: 8px; border: none;
                            background: linear-gradient(135deg, #dc2626, #b91c1c);
                            color: white; cursor: pointer; font-size: 15px; font-weight: 600;
                        "
                    >🗑️ Ҳа, ўчириш</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    },

    async executDelete(topicId) {
        const btn = document.getElementById('confirmDeleteBtn');
        if (btn) { btn.textContent = 'Ўчирилмоқда...'; btn.disabled = true; }

        try {
            await API.deleteTopic(topicId);
            document.getElementById('deleteTopicModal')?.remove();
            Topics.showToast('✅ Мавзу муваффақиятли ўчирилди!', 'success');
            await this.loadTopics();
        } catch (e) {
            document.getElementById('deleteTopicModal')?.remove();
            Topics.showToast(`❌ Хато: ${e.message}`, 'error');
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
                background: #fff;
                border-radius: 16px;
                padding: 32px;
                max-width: 480px;
                width: 90%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            ">
                <h2 style="margin:0 0 20px 0;">+ Янги мавзу қўшиш</h2>
                <div style="margin-bottom:16px;">
                    <label style="display:block; margin-bottom:6px; font-weight:600;">Қисқа номи</label>
                    <input id="topicShortName" type="text" placeholder="Масалан: Экология" style="
                        width:100%; padding:10px 14px; border-radius:8px;
                        border:2px solid #e5e7eb; font-size:15px; box-sizing:border-box;
                    ">
                </div>
                <div style="margin-bottom:24px;">
                    <label style="display:block; margin-bottom:6px; font-weight:600;">Тўлиқ номи</label>
                    <input id="topicFullName" type="text" placeholder="Масалан: Экологик экспертиза асослари" style="
                        width:100%; padding:10px 14px; border-radius:8px;
                        border:2px solid #e5e7eb; font-size:15px; box-sizing:border-box;
                    ">
                </div>
                <div style="display:flex; gap:12px; justify-content:flex-end;">
                    <button onclick="document.getElementById('createTopicModal').remove()"
                        style="padding:10px 20px; border-radius:8px; border:2px solid #e5e7eb;
                        background:transparent; cursor:pointer; font-size:14px; font-weight:600;">
                        Бекор қилиш
                    </button>
                    <button id="saveTopicBtn" onclick="Topics.submitCreate()"
                        style="padding:10px 20px; border-radius:8px; border:none;
                        background:#166534; color:white; cursor:pointer; font-size:14px; font-weight:700;">
                        Сақлаш
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
        if (!short || !full) { alert('Илтимос, иккала майдонни ҳам тўлдиринг!'); return; }

        const btn = document.getElementById('saveTopicBtn');
        if (btn) { btn.textContent = 'Сақланмоқда...'; btn.disabled = true; }

        try {
            await API.createTopic({ short_name: short, full_name: full });
            document.getElementById('createTopicModal')?.remove();
            Topics.showToast('✅ Янги мавзу муваффақиятли яратилди!', 'success');
            await this.loadTopics();
        } catch (e) {
            if (btn) { btn.textContent = 'Сақлаш'; btn.disabled = false; }
            alert('Хатолик: ' + (e.message || e));
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    Topics.init();

    // Listen to nav button clicks
    const btn = document.querySelector('[data-target="topics"]');
    if (btn) {
        btn.addEventListener('click', () => Topics.init());
    }

    // Listen to hash changes
    window.addEventListener('hashchange', () => {
        if (window.location.hash === '#topics') {
            Topics.init();
        }
    });
});
