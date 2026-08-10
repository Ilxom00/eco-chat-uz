const Questions = {
    currentTopicId: null,
    currentTopicName: '',
    currentPage: 1,
    questionsMap: {},

    loadForTopic(topicId, topicName) {
        this.currentTopicId = topicId;
        this.currentTopicName = topicName;
        this.currentPage = 1;

        document.getElementById('pageTitle').textContent = `Саволлар: ${topicName}`;
        const topicsSection = document.getElementById('topics');
        if (!topicsSection) return;

        topicsSection.innerHTML = `
            <div class="section-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
                <button class="btn btn-outline" onclick="Questions.backToTopics()" style="display:flex;align-items:center;gap:6px;">
                    <span>←</span> <span>Ортга</span>
                </button>
                <div style="display:flex; gap:12px;">
                    <button class="btn btn-primary" onclick="Questions.showAddModal('${topicId}')" style="background:#166534;color:#fff;border:none;border-radius:8px;padding:9px 18px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px;">
                        <span>+</span> <span>Савол қўшиш</span>
                    </button>
                    <button class="btn btn-outline" onclick="Questions.showImportModal('${topicId}')" style="border:1px solid #166534;color:#166534;border-radius:8px;padding:9px 18px;font-weight:600;cursor:pointer;">
                        Excel дан юклаш
                    </button>
                </div>
            </div>

            <div class="table-container" style="background:#fff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                <table class="data-table" style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="background:#f8fafc;border-bottom:1px solid #e5e7eb;">
                            <th style="padding:12px;width:50px;text-align:center;font-size:12px;font-weight:700;color:#6b7280;">№</th>
                            <th style="padding:12px;text-align:left;font-size:12px;font-weight:700;color:#6b7280;">САВОЛ МАТНИ</th>
                            <th style="padding:12px;text-align:left;font-size:12px;font-weight:700;color:#166534;">ТЎҒРИ ЖАВОБ</th>
                            <th style="padding:12px;width:180px;text-align:center;font-size:12px;font-weight:700;color:#6b7280;">АМАЛЛАР</th>
                        </tr>
                    </thead>
                    <tbody id="questionsList">
                        <tr><td colspan="4" style="text-align:center;padding:32px;color:#6b7280;">Юкланмоқда...</td></tr>
                    </tbody>
                </table>
            </div>

            <div id="questionsPagination" style="margin-top:20px;"></div>
        `;

        this.fetchQuestions(topicId, 1);
    },

    backToTopics() {
        document.getElementById('pageTitle').textContent = 'Тест Киритиш';
        const topicsSection = document.getElementById('topics');
        if (!topicsSection) return;

        topicsSection.innerHTML = `
            <div class="section-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2>Мавзулар</h2>
                <button class="btn btn-primary" onclick="Topics.showCreateModal()">+ Янги мавзу</button>
            </div>
            <div id="topicsList" class="topics-grid"></div>
        `;
        Topics.init();
    },

    async fetchQuestions(topicId, page = 1) {
        this.currentPage = page;
        const tbody = document.getElementById('questionsList');
        if (!tbody) return;

        try {
            const res = await API.getQuestions(topicId, { page, page_size: 10 });
            const items = res.items || [];
            const total = res.total || 0;

            this.questionsMap = {};
            items.forEach(q => {
                this.questionsMap[q.id] = q;
            });

            if (items.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" style="text-align:center;padding:48px;color:#9ca3af;">
                            <div style="font-size:36px;margin-bottom:8px;">📝</div>
                            <div style="font-size:15px;font-weight:600;">Ушбу мавзуда ҳали саволлар йўқ</div>
                            <div style="font-size:13px;margin-top:4px;">Юқоридаги "+ Савол қўшиш" тугмаси орқали савол қўшинг</div>
                        </td>
                    </tr>`;
                document.getElementById('questionsPagination').innerHTML = '';
                return;
            }

            tbody.innerHTML = items.map((q, idx) => {
                const globalIndex = (page - 1) * 10 + idx + 1;
                const safeText = (q.text || '').replace(/'/g, "\\'");
                return `
                    <tr style="border-bottom:1px solid #e5e7eb;transition:background 0.15s;" onmouseover="this.style.background='#f0fdf4'" onmouseout="this.style.background='#fff'">
                        <td style="padding:12px;text-align:center;font-weight:700;color:#9ca3af;font-size:13px;">${globalIndex}</td>
                        <td style="padding:12px;font-size:14px;color:#111827;font-weight:600;line-height:1.4;">${q.text}</td>
                        <td style="padding:12px;font-size:13px;color:#166534;font-weight:700;">
                            <span style="background:#dcfce7;padding:4px 10px;border-radius:16px;">✅ ${q.correct_answer}</span>
                        </td>
                        <td style="padding:12px;text-align:center;">
                            <div style="display:inline-flex;gap:8px;">
                                <button onclick="Questions.showEditModal('${q.id}')"
                                    style="background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px;font-weight:700;display:inline-flex;align-items:center;gap:4px;box-shadow:0 2px 6px rgba(37,99,235,0.2);">
                                    ✏️ Таҳрирлаш
                                </button>
                                <button onclick="Questions.confirmDeleteQuestion('${q.id}', '${safeText}')"
                                    style="background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px;font-weight:700;display:inline-flex;align-items:center;gap:4px;box-shadow:0 2px 6px rgba(220,38,38,0.2);">
                                    🗑️ Ўчириш
                                </button>
                            </div>
                        </td>
                    </tr>`;
            }).join('');

            this.renderPagination(total, page);

        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:24px;color:#dc2626;">Хатолик: ${e.message}</td></tr>`;
        }
    },

    renderPagination(total, page) {
        const container = document.getElementById('questionsPagination');
        if (!container) return;
        const totalPages = Math.ceil(total / 10);
        if (totalPages <= 1) { container.innerHTML = ''; return; }

        let html = '<div style="display:flex;gap:8px;justify-content:center;margin-top:16px;">';
        for (let p = 1; p <= totalPages; p++) {
            const active = p === page
                ? 'background:#166534;color:#fff;box-shadow:0 4px 12px rgba(22,101,52,0.3);'
                : 'background:#f3f4f6;color:#374151;';
            html += `<button onclick="Questions.fetchQuestions('${this.currentTopicId}', ${p})" style="${active}border:none;border-radius:8px;padding:8px 16px;cursor:pointer;font-weight:700;font-size:13px;">${p}</button>`;
        }
        html += '</div>';
        container.innerHTML = html;
    },

    showAddModal(topicId) {
        document.getElementById('addQuestionModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'addQuestionModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.65);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:#fff;border-radius:20px;padding:32px;max-width:560px;width:92%;box-shadow:0 24px 64px rgba(0,0,0,0.3);max-height:90vh;overflow-y:auto;">
                <h2 style="margin:0 0 20px 0;color:#111827;font-size:20px;display:flex;align-items:center;gap:8px;">
                    <span>➕</span> <span>Янги савол қўшиш</span>
                </h2>

                <div style="margin-bottom:20px;">
                    <label style="display:block;margin-bottom:6px;font-weight:700;font-size:13px;color:#374151;">Савол матни:</label>
                    <textarea id="newQuestionText" rows="3" placeholder="Саволни киритинг..." style="width:100%;padding:12px;border-radius:10px;border:2px solid #e5e7eb;font-size:14px;box-sizing:border-box;font-family:inherit;resize:vertical;"></textarea>
                </div>

                <div style="font-weight:700;font-size:13px;color:#374151;margin-bottom:10px;">4 та вариант (тўғри жавобни танланг):</div>

                ${['A', 'B', 'C', 'D'].map((label, idx) => `
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;background:#f9fafb;padding:10px 14px;border-radius:10px;border:1px solid #e5e7eb;">
                        <input type="radio" name="correctAnswerRadio" id="radio_${label}" value="${idx}" ${idx === 0 ? 'checked' : ''} style="width:18px;height:18px;cursor:pointer;accent-color:#166534;">
                        <label for="radio_${label}" style="font-weight:800;font-size:14px;color:#166534;width:24px;">${label}:</label>
                        <input type="text" id="ans_input_${idx}" placeholder="${label} вариант жавоби" style="flex:1;padding:8px 12px;border-radius:8px;border:1px solid #d1d5db;font-size:14px;">
                    </div>
                `).join('')}

                <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:24px;padding-top:16px;border-top:1px solid #e5e7eb;">
                    <button onclick="document.getElementById('addQuestionModal').remove()" style="padding:10px 22px;border-radius:10px;border:2px solid #e5e7eb;background:#fff;cursor:pointer;font-size:14px;font-weight:600;color:#374151;">Бекор қилиш</button>
                    <button id="saveQuestionBtn" onclick="Questions.submitAddQuestion('${topicId}')" style="padding:10px 24px;border-radius:10px;border:none;background:#166534;color:#fff;cursor:pointer;font-size:14px;font-weight:700;">💾 Сақлаш</button>
                </div>
            </div>`;

        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
        document.getElementById('newQuestionText').focus();
    },

    async submitAddQuestion(topicId) {
        const text = document.getElementById('newQuestionText').value.trim();
        if (!text) { alert('Илтимос, савол матнини киритинг!'); return; }

        const answers = [];
        const selectedCorrectIdx = parseInt(document.querySelector('input[name="correctAnswerRadio"]:checked').value, 10);

        for (let i = 0; i < 4; i++) {
            const val = document.getElementById(`ans_input_${i}`).value.trim();
            if (!val) { alert(`Илтимос, барча 4 та вариантни тўлдиринг (${['A','B','C','D'][i]} вариант бўш)!`); return; }
            answers.push({
                text: val,
                is_correct: (i === selectedCorrectIdx),
                option_label: ['A', 'B', 'C', 'D'][i]
            });
        }

        const btn = document.getElementById('saveQuestionBtn');
        if (btn) { btn.textContent = 'Сақланмоқда...'; btn.disabled = true; }

        try {
            await API.createQuestion(topicId, { text, answers });
            document.getElementById('addQuestionModal')?.remove();
            
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;padding:14px 20px;border-radius:12px;font-weight:700;background:#16a34a;color:#fff;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,0.2);';
            toast.textContent = '✅ Янги савол муваффақиятли қўшилди!';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);

            this.fetchQuestions(topicId, this.currentPage);

        } catch (e) {
            if (btn) { btn.textContent = '💾 Сақлаш'; btn.disabled = false; }
            alert('Хатолик: ' + (e.message || e));
        }
    },

    showEditModal(qId) {
        const q = this.questionsMap[qId];
        if (!q) return;

        document.getElementById('editQuestionModal')?.remove();

        const options = q.options || ['', '', '', ''];
        const correctText = q.correct_answer || '';
        let correctIdx = 0;

        options.forEach((opt, idx) => {
            if (opt === correctText) correctIdx = idx;
        });

        const modal = document.createElement('div');
        modal.id = 'editQuestionModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.65);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:#fff;border-radius:20px;padding:32px;max-width:560px;width:92%;box-shadow:0 24px 64px rgba(0,0,0,0.3);max-height:90vh;overflow-y:auto;">
                <h2 style="margin:0 0 20px 0;color:#111827;font-size:20px;display:flex;align-items:center;gap:8px;">
                    <span>✏️</span> <span>Саволни таҳрирлаш</span>
                </h2>

                <div style="margin-bottom:20px;">
                    <label style="display:block;margin-bottom:6px;font-weight:700;font-size:13px;color:#374151;">Савол матни:</label>
                    <textarea id="editQuestionText" rows="3" style="width:100%;padding:12px;border-radius:10px;border:2px solid #e5e7eb;font-size:14px;box-sizing:border-box;font-family:inherit;resize:vertical;">${q.text || ''}</textarea>
                </div>

                <div style="font-weight:700;font-size:13px;color:#374151;margin-bottom:10px;">4 та вариант (тўғри жавобни танланг):</div>

                ${['A', 'B', 'C', 'D'].map((label, idx) => `
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;background:#f9fafb;padding:10px 14px;border-radius:10px;border:1px solid #e5e7eb;">
                        <input type="radio" name="editCorrectAnswerRadio" id="edit_radio_${label}" value="${idx}" ${idx === correctIdx ? 'checked' : ''} style="width:18px;height:18px;cursor:pointer;accent-color:#166534;">
                        <label for="edit_radio_${label}" style="font-weight:800;font-size:14px;color:#166534;width:24px;">${label}:</label>
                        <input type="text" id="edit_ans_input_${idx}" value="${(options[idx] || '').replace(/"/g, '&quot;')}" placeholder="${label} вариант жавоби" style="flex:1;padding:8px 12px;border-radius:8px;border:1px solid #d1d5db;font-size:14px;">
                    </div>
                `).join('')}

                <div style="display:flex;gap:12px;justify-content:flex-end;margin-top:24px;padding-top:16px;border-top:1px solid #e5e7eb;">
                    <button onclick="document.getElementById('editQuestionModal').remove()" style="padding:10px 22px;border-radius:10px;border:2px solid #e5e7eb;background:#fff;cursor:pointer;font-size:14px;font-weight:600;color:#374151;">Бекор қилиш</button>
                    <button id="updateQuestionBtn" onclick="Questions.submitEditQuestion('${qId}')" style="padding:10px 24px;border-radius:10px;border:none;background:#2563eb;color:#fff;cursor:pointer;font-size:14px;font-weight:700;">💾 Ўзгаришларни сақлаш</button>
                </div>
            </div>`;

        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
        document.getElementById('editQuestionText').focus();
    },

    async submitEditQuestion(qId) {
        const text = document.getElementById('editQuestionText').value.trim();
        if (!text) { alert('Илтимос, савол матнини киритинг!'); return; }

        const answers = [];
        const selectedCorrectIdx = parseInt(document.querySelector('input[name="editCorrectAnswerRadio"]:checked').value, 10);

        for (let i = 0; i < 4; i++) {
            const val = document.getElementById(`edit_ans_input_${i}`).value.trim();
            if (!val) { alert(`Илтимос, барча 4 та вариантни тўлдиринг (${['A','B','C','D'][i]} вариант бўш)!`); return; }
            answers.push({
                text: val,
                is_correct: (i === selectedCorrectIdx),
                option_label: ['A', 'B', 'C', 'D'][i]
            });
        }

        const btn = document.getElementById('updateQuestionBtn');
        if (btn) { btn.textContent = 'Сақланмоқда...'; btn.disabled = true; }

        try {
            await API.updateQuestion(qId, { text, answers });
            document.getElementById('editQuestionModal')?.remove();
            
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;padding:14px 20px;border-radius:12px;font-weight:700;background:#16a34a;color:#fff;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,0.2);';
            toast.textContent = '✅ Савол муваффақиятли таҳрирланди!';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);

            this.fetchQuestions(this.currentTopicId, this.currentPage);

        } catch (e) {
            if (btn) { btn.textContent = '💾 Ўзгаришларни сақлаш'; btn.disabled = false; }
            alert('Хатолик: ' + (e.message || e));
        }
    },

    confirmDeleteQuestion(qId, qText) {
        document.getElementById('deleteQModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'deleteQModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.65);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:#fff;border-radius:20px;padding:32px;max-width:440px;width:90%;box-shadow:0 24px 64px rgba(0,0,0,0.3);text-align:center;">
                <div style="font-size:48px;margin-bottom:12px;">⚠️</div>
                <h2 style="margin:0 0 10px 0;color:#dc2626;font-size:20px;">Саволни ўчириш</h2>
                <p style="color:#6b7280;margin:0 0 24px;font-size:14px;line-height:1.5;">
                    Ушбу саволни базадан бутунлай ўчирасизми?<br>
                    <strong style="color:#111827;display:block;margin-top:8px;">"${qText}"</strong>
                </p>
                <div style="display:flex;gap:12px;justify-content:center;">
                    <button onclick="document.getElementById('deleteQModal').remove()" style="padding:10px 24px;border-radius:10px;border:2px solid #e5e7eb;background:#fff;cursor:pointer;font-size:14px;font-weight:600;color:#374151;">Бекор қилиш</button>
                    <button id="execDeleteQBtn" onclick="Questions.executeDeleteQuestion('${qId}')" style="padding:10px 24px;border-radius:10px;border:none;background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff;cursor:pointer;font-size:14px;font-weight:700;">🗑️ Ҳа, ўчириш</button>
                </div>
            </div>`;

        document.body.appendChild(modal);
        modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    },

    async executeDeleteQuestion(qId) {
        const btn = document.getElementById('execDeleteQBtn');
        if (btn) { btn.textContent = 'Ўчирилмоқда...'; btn.disabled = true; }

        try {
            await API.deleteQuestion(qId);
            document.getElementById('deleteQModal')?.remove();
            
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;padding:14px 20px;border-radius:12px;font-weight:700;background:#16a34a;color:#fff;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,0.2);';
            toast.textContent = '✅ Савол базадан ўчирилди!';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);

            this.fetchQuestions(this.currentTopicId, this.currentPage);

        } catch (e) {
            document.getElementById('deleteQModal')?.remove();
            alert('Хатолик: ' + (e.message || e));
        }
    },

    showImportModal(topicId) {
        alert('Excel орқали саволларни оммавий юклаш учун тизим тайёрланади.');
    }
};
