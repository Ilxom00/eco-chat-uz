const Questions = {
    loadForTopic(topicId, topicName) {
        document.getElementById('pageTitle').textContent = `Саволлар: ${topicName}`;
        const topicsSection = document.getElementById('topics');
        
        topicsSection.innerHTML = `
            <div class="section-header" style="display:flex; justify-content:space-between; margin-bottom:20px;">
                <button class="btn btn-outline" onclick="Questions.backToTopics()">← Ортга</button>
                <div style="display:flex; gap:12px;">
                    <button class="btn btn-primary" onclick="Questions.showAddModal(${topicId})">+ Савол қўшиш</button>
                    <button class="btn btn-outline" onclick="Questions.showImportModal(${topicId})">Excel дан юклаш</button>
                </div>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>№</th>
                            <th>Савол матни</th>
                            <th>Тўғри жавоб</th>
                            <th>Амаллар</th>
                        </tr>
                    </thead>
                    <tbody id="questionsList">
                        <!-- Questions here -->
                    </tbody>
                </table>
            </div>
        `;

        this.fetchQuestions(topicId);
    },

    backToTopics() {
        document.getElementById('pageTitle').textContent = 'Тест Киритиш';
        const topicsSection = document.getElementById('topics');
        topicsSection.innerHTML = `
            <div class="section-header">
                <h2>Мавзулар</h2>
                <button class="btn btn-primary" onclick="Topics.showCreateModal()">+ Янги мавзу</button>
            </div>
            <div id="topicsList" class="topics-grid"></div>
        `;
        Topics.init();
    },

    async fetchQuestions(topicId) {
        try {
            // MOCK DATA
            const data = [
                { id: 1, text: 'Ўзбекистонда экология вазирлиги қачон ташкил этилган?', correct_answer: '2023 йил', options: ['2023 йил', '2020 йил', '2018 йил', '2021 йил'] }
            ];

            const tbody = document.getElementById('questionsList');
            tbody.innerHTML = data.map((q, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${q.text}</td>
                    <td style="color:var(--success); font-weight:500;">${q.correct_answer}</td>
                    <td>
                        <button class="btn btn-outline input-sm">Ўчириш</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {
            console.error(e);
        }
    },

    showAddModal(topicId) {
        alert('Add question form modal');
    },

    showImportModal(topicId) {
        alert('Import Excel modal');
    }
};
