const Topics = {
    init() {
        this.loadTopics();
    },

    async loadTopics() {
        const container = document.getElementById('topicsList');
        if (!container) return;

        try {
            // MOCK DATA
            const topics = [
                { id: 1, short_name: 'Экология', full_name: 'Экология ва атроф-муҳит муҳофазаси асослари', q_count: 45 },
                { id: 2, short_name: 'Чиқиндилар', full_name: 'Чиқиндилар билан ишлаш тартиби', q_count: 30 }
            ];

            container.innerHTML = topics.map(t => `
                <div class="kpi-card" style="display:flex; justify-content:space-between; cursor:pointer;" onclick="Questions.loadForTopic(${t.id}, '${t.short_name}')">
                    <div>
                        <h3>${t.short_name}</h3>
                        <div style="font-size:14px; color:var(--text-secondary); margin-top:8px;">${t.full_name}</div>
                    </div>
                    <div style="text-align:right;">
                        <div class="badge badge-success">${t.q_count} савол</div>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            console.error(e);
        }
    },

    showCreateModal() {
        // MOCK modal for topic creation
        alert('Create topic modal will open here');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Basic router logic initialized Topics when visible
    document.querySelector('[data-target="topics"]').addEventListener('click', () => {
        Topics.init();
    });
});
