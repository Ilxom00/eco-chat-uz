const Topics = {
    init() {
        this.loadTopics();
    },

    async loadTopics() {
        const container = document.getElementById('topicsList');
        if (!container) return;
        container.innerHTML = '<div style="padding:24px;color:#6b7280;font-weight:600;">Юкланмоқда...</div>';

        try {
            let topics = await API.getTopics();

            // Auto force-reseed if DB is missing topics or has fewer than 4 topics
            if (!topics || !Array.isArray(topics) || topics.length < 4) {
                try {
                    await API.fetch('/topics/reseed', { method: 'POST' });
                    topics = await API.getTopics();
                } catch (reseedErr) {
                    console.error('Reseed error:', reseedErr);
                }
            }

            if (!topics || !Array.isArray(topics) || topics.length === 0) {
                // Second attempt reseed
                try {
                    await API.fetch('/topics/reseed', { method: 'POST' });
                    topics = await API.getTopics();
                } catch (e) {}
            }

            if (!topics || !Array.isArray(topics) || topics.length === 0) {
                container.innerHTML = '<div style="padding:24px;color:#dc2626;font-weight:600;">Мавзулар юкланмоқда... Саҳифани (F5) босиб қайта янгиланг.</div>';
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
                                display: inline-flex;
                                align-items: center;
                                gap: 6px;
                                box-shadow: 0 2px 6px rgba(220, 38, 38, 0.2);
                            "
                        >
                            🗑️ Ўчириш
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (e) {
            console.error('Failed to load topics:', e);
            // Auto trigger reseed and reload
            try {
                await API.fetch('/topics/reseed', { method: 'POST' });
                const topics = await API.getTopics();
                if (topics && Array.isArray(topics) && topics.length > 0) {
                    this.loadTopics();
                    return;
                }
            } catch (err) {}
            container.innerHTML = `<div style="padding:24px;color:#dc2626;font-weight:600;">Хатолик: ${e.message}. Саҳифани қайта янгиланг.</div>`;
        }
    },

    showCreateModal() {
        document.getElementById('createTopicModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'createTopicModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.65);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:#fff;border-radius:20px;padding:32px;max-width:480px;width:90%;box-shadow:0 24px 64px rgba(0,0,0,0.3);">
                <h2 style="margin:0 0 20px 0;color:#111827;font-size:20px;">➕ Янги мавзу қўшиш</h2>
                <div style="margin-bottom:16px;">
                    <label style="display:block;margin-bottom:6px;font-weight:600;font-size:13px;color:#374151;">Қисқа номи (масалан: 5-Мавзу):</label>
                    <input type="text" id="newTopicShortName" placeholder="5-Мавзу" style="width:100%;padding:10px 14px;border-radius:8px;border:1px solid #d1d5db;font-size:14px;box-sizing:border-box;">
                </div>
                <div style="margin-bottom:24px;">
                    <label style="display:block;margin-bottom:6px;font-weight:600;font-size:13px;color:#374151;">Тўлиқ номи:</label>
                    <input type="text" id="newTopicFullName" placeholder="Мавзунинг тўлиқ номи..." style="width:100%;padding:10px 14px;border-radius:8px;border:1px solid #d1d5db;font-size:14px;box-sizing:border-box;">
                </div>
                <div style="display:flex;gap:12px;justify-content:flex-end;">
                    <button onclick="document.getElementById('createTopicModal').remove()" style="padding:10px 20px;border-radius:8px;border:1px solid #d1d5db;background:#fff;cursor:pointer;font-size:14px;font-weight:600;">Бекор қилиш</button>
                    <button id="saveTopicBtn" onclick="Topics.submitCreateTopic()" style="padding:10px 20px;border-radius:8px;border:none;background:#166534;color:#fff;cursor:pointer;font-size:14px;font-weight:600;">💾 Сақлаш</button>
                </div>
            </div>`;

        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
        document.getElementById('newTopicShortName').focus();
    },

    async submitCreateTopic() {
        const shortName = document.getElementById('newTopicShortName').value.trim();
        const fullName = document.getElementById('newTopicFullName').value.trim();

        if (!shortName || !fullName) {
            alert('Илтимос, мавзунинг қисқа ва тўлиқ номларини киритинг!');
            return;
        }

        const btn = document.getElementById('saveTopicBtn');
        if (btn) { btn.textContent = 'Сақланмоқда...'; btn.disabled = true; }

        try {
            await API.createTopic({ short_name: shortName, full_name: fullName });
            document.getElementById('createTopicModal')?.remove();
            
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;padding:14px 20px;border-radius:12px;font-weight:700;background:#16a34a;color:#fff;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,0.2);';
            toast.textContent = '✅ Янги мавзу муваффақиятли қўшилди!';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);

            this.loadTopics();
        } catch (e) {
            if (btn) { btn.textContent = '💾 Сақлаш'; btn.disabled = false; }
            alert('Хатолик: ' + (e.message || e));
        }
    },

    confirmDelete(topicId, topicName) {
        document.getElementById('deleteTopicModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'deleteTopicModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.65);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:#fff;border-radius:20px;padding:32px;max-width:440px;width:90%;box-shadow:0 24px 64px rgba(0,0,0,0.3);text-align:center;">
                <div style="font-size:48px;margin-bottom:12px;">⚠️</div>
                <h2 style="margin:0 0 10px 0;color:#dc2626;font-size:20px;">Мавзуни ўчириш</h2>
                <p style="color:#6b7280;margin:0 0 24px;font-size:14px;line-height:1.5;">
                    Сиз чиндан ҳам <strong style="color:#111827;">"${topicName}"</strong> мавзусини ва унга тегишли <strong>барча саволларни</strong> базадан ўчирмоқчимисиз?<br>
                    <span style="color:#dc2626;font-size:12px;display:block;margin-top:6px;">Бу амални ортга қайтариб бўлмайди!</span>
                </p>
                <div style="display:flex;gap:12px;justify-content:center;">
                    <button onclick="document.getElementById('deleteTopicModal').remove()" style="padding:10px 24px;border-radius:10px;border:2px solid #e5e7eb;background:#fff;cursor:pointer;font-size:14px;font-weight:600;color:#374151;">Бекор қилиш</button>
                    <button id="execDeleteTopicBtn" onclick="Topics.executeDelete('${topicId}')" style="padding:10px 24px;border-radius:10px;border:none;background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff;cursor:pointer;font-size:14px;font-weight:700;">🗑️ Ҳа, ўчириш</button>
                </div>
            </div>`;

        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    },

    async executeDelete(topicId) {
        const btn = document.getElementById('execDeleteTopicBtn');
        if (btn) { btn.textContent = 'Ўчирилмоқда...'; btn.disabled = true; }

        try {
            await API.deleteTopic(topicId);
            document.getElementById('deleteTopicModal')?.remove();
            
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;padding:14px 20px;border-radius:12px;font-weight:700;background:#16a34a;color:#fff;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,0.2);';
            toast.textContent = '✅ Мавзу ва унинг барча саволлари ўчирилди!';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);

            this.loadTopics();
        } catch (e) {
            document.getElementById('deleteTopicModal')?.remove();
            alert('Хатолик: ' + (e.message || e));
        }
    }
};
