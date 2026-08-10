const Employees = {
    showDetail(empId) {
        const emp = (typeof Dashboard !== 'undefined' && Dashboard.employeesMap) 
            ? Dashboard.employeesMap[empId] 
            : null;

        const modal = document.getElementById('employeeModal');
        const body = document.getElementById('employeeModalBody');
        if (!modal || !body) return;

        if (!emp) {
            body.innerHTML = `<div style="padding:24px;text-align:center;color:#ef4444;font-weight:700;">Маълумот топилмади</div>`;
            modal.style.display = 'flex';
            return;
        }

        // Initials for avatar
        const parts = (emp.name || '').trim().split(' ');
        const initials = parts.length >= 2 
            ? (parts[0][0] + parts[1][0]).toUpperCase()
            : (emp.name ? emp.name.slice(0, 2).toUpperCase() : '👤');

        // Topic table rows
        const topicRows = (emp.topics || []).map((t, idx) => {
            let s1 = '<span style="color:#9ca3af;">—</span>';
            if (t.attempt1 !== null && t.attempt1 !== undefined) {
                const attId = t.attempt1_id || '';
                s1 = `<button onclick="Employees.showAttemptModal('${attId}', '${emp.id}', '${t.topic_id || ''}', 1)" style="background:#dbeafe;color:#1e40af;border:1px solid #bfdbfe;padding:4px 10px;border-radius:8px;font-weight:700;font-size:12px;cursor:pointer;display:inline-flex;align-items:center;gap:4px;transition:all 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'" title="15 та савол ва жавобларни кўриш учун босинг"><span>${t.attempt1}%</span> <span style="font-size:11px;">🔍</span></button>`;
            }

            let s2 = '<span style="color:#9ca3af;">—</span>';
            if (t.attempt2 !== null && t.attempt2 !== undefined) {
                const attId = t.attempt2_id || '';
                s2 = `<button onclick="Employees.showAttemptModal('${attId}', '${emp.id}', '${t.topic_id || ''}', 2)" style="background:#dcfce7;color:#166534;border:1px solid #bbf7d0;padding:4px 10px;border-radius:8px;font-weight:700;font-size:12px;cursor:pointer;display:inline-flex;align-items:center;gap:4px;transition:all 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'" title="15 та савол ва жавобларни кўриш учун босинг"><span>${t.attempt2}%</span> <span style="font-size:11px;">🔍</span></button>`;
            }

            const diff = t.diff !== null && t.diff !== undefined
                ? `<span style="font-weight:700;color:${t.diff > 0 ? '#16a34a' : t.diff < 0 ? '#dc2626' : '#6b7280'}">${t.diff > 0 ? '+' : ''}${t.diff}%</span>`
                : '<span style="color:#9ca3af;">—</span>';

            let holatBg = '#f3f4f6'; let holatC = '#6b7280'; let holatT = '—';
            if (t.holat === 'Тугатган') { holatBg = '#dcfce7'; holatC = '#166534'; holatT = '✅ Тугатган'; }
            else if (t.holat === '1-уринди') { holatBg = '#fef9c3'; holatC = '#854d0e'; holatT = '🔁 1-уринди'; }
            else if (t.holat === 'Жараёнда') { holatBg = '#dbeafe'; holatC = '#1e40af'; holatT = '🔄 Жараёнда'; }

            return `
                <tr style="border-bottom:1px solid #e5e7eb;">
                    <td style="padding:10px 12px;font-size:13px;font-weight:600;color:#1f2937;">${idx + 1}-Мавзу — ${t.short_name || ''}</td>
                    <td style="padding:10px;text-align:center;font-size:13px;">${s1}</td>
                    <td style="padding:10px;text-align:center;font-size:13px;">${s2}</td>
                    <td style="padding:10px;text-align:center;font-size:13px;">${diff}</td>
                    <td style="padding:10px;text-align:center;">
                        <span style="background:${holatBg};color:${holatC};padding:4px 9px;border-radius:20px;font-size:11px;font-weight:700;">${holatT}</span>
                    </td>
                </tr>`;
        }).join('');

        const tot = emp.total || {};
        const ta1 = tot.avg1 !== null && tot.avg1 !== undefined ? `${tot.avg1}%` : '—';
        const ta2 = tot.avg2 !== null && tot.avg2 !== undefined ? `${tot.avg2}%` : '—';
        const tdiff = tot.diff !== null && tot.diff !== undefined 
            ? `${tot.diff > 0 ? '+' : ''}${tot.diff}%`
            : '—';

        const safeName = (emp.name || '').replace(/'/g, "\\'");

        body.innerHTML = `
            <!-- Employee Card Header -->
            <div style="display:flex;align-items:center;gap:18px;background:linear-gradient(135deg,#0d1f0f,#1b5e20);padding:20px 24px;border-radius:16px;color:#fff;margin-bottom:20px;box-shadow:0 8px 24px rgba(27,94,32,0.25);">
                <div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#2e7d32,#4caf50);display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:#fff;box-shadow:0 4px 12px rgba(0,0,0,0.2);">
                    ${initials}
                </div>
                <div style="flex:1;">
                    <div style="font-size:18px;font-weight:800;letter-spacing:-0.3px;">${emp.name}</div>
                    <div style="font-size:13px;opacity:0.9;margin-top:4px;display:flex;align-items:center;gap:6px;">
                        <span>🏢</span>
                        <span>${emp.branch || '—'}</span>
                    </div>
                </div>
            </div>

            <!-- Detailed Test Scores Table -->
            <div style="margin-bottom:20px;">
                <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:10px;display:flex;align-items:center;gap:6px;">
                    <span>📊</span>
                    <span>Мавзулар бўйича тест кўрсаткичлари</span>
                    <span style="font-size:11px;color:#6b7280;font-weight:400;margin-left:auto;">(Уриниш фоизини босиб 15 та савол ва жавобларни кўришингиз мумкин)</span>
                </div>
                <div style="border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                    <table style="width:100%;border-collapse:collapse;background:#fff;">
                        <thead>
                            <tr style="background:#f8fafc;border-bottom:1px solid #e5e7eb;">
                                <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;">Мавзу</th>
                                <th style="padding:10px;text-align:center;font-size:11px;font-weight:700;color:#1e40af;text-transform:uppercase;">1-уриниш</th>
                                <th style="padding:10px;text-align:center;font-size:11px;font-weight:700;color:#166534;text-transform:uppercase;">2-уриниш</th>
                                <th style="padding:10px;text-align:center;font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Фарқ</th>
                                <th style="padding:10px;text-align:center;font-size:11px;font-weight:700;color:#374151;text-transform:uppercase;">Ҳолат</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${topicRows}
                            <!-- Total Summary Row -->
                            <tr style="background:#f0fdf4;font-weight:700;border-top:2px solid #bbf7d0;">
                                <td style="padding:12px;font-size:13px;color:#166534;">🏆 ЖАМИ ЎРТАЧА</td>
                                <td style="padding:12px;text-align:center;font-size:14px;color:#1e40af;">${ta1}</td>
                                <td style="padding:12px;text-align:center;font-size:14px;color:#166534;">${ta2}</td>
                                <td style="padding:12px;text-align:center;font-size:14px;color:#0f766e;">${tdiff}</td>
                                <td style="padding:12px;text-align:center;">—</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Footer Action Buttons -->
            <div style="display:flex;justify-content:space-between;align-items:center;padding-top:16px;border-top:1px solid #e5e7eb;">
                <button onclick="Employees.closeModal(); Dashboard.confirmDeleteEmployee('${emp.id}', '${safeName}')"
                    style="background:linear-gradient(135deg,#dc2626,#b91c1c);color:#fff;border:none;border-radius:10px;padding:10px 20px;cursor:pointer;font-size:13px;font-weight:700;display:flex;align-items:center;gap:6px;box-shadow:0 4px 12px rgba(220,38,38,0.25);transition:transform .15s;"
                    onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                    <span>🗑️</span>
                    <span>Ходимни базадан ўчириш</span>
                </button>

                <button onclick="Employees.closeModal()"
                    style="background:#f3f4f6;color:#374151;border:1px solid #d1d5db;border-radius:10px;padding:10px 20px;cursor:pointer;font-size:13px;font-weight:600;">
                    Ёпиш
                </button>
            </div>
        `;

        modal.style.display = 'flex';

        const closeBtn = modal.querySelector('.close-modal');
        if (closeBtn) closeBtn.onclick = () => Employees.closeModal();

        modal.onclick = (e) => {
            if (e.target === modal) Employees.closeModal();
        };
    },

    closeModal() {
        const modal = document.getElementById('employeeModal');
        if (modal) modal.style.display = 'none';
    },

    async showAttemptModal(attemptId, empId, topicId, attemptNum = 1) {
        document.getElementById('attemptDetailModal')?.remove();
        
        const modal = document.createElement('div');
        modal.id = 'attemptDetailModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:100000;background:rgba(0,0,0,0.65);backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;padding:20px;';
        
        modal.innerHTML = `
            <div style="background:#fff;border-radius:20px;max-width:850px;width:100%;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,0.3);overflow:hidden;">
                <div style="display:flex;justify-content:space-between;align-items:center;padding:20px 24px;background:#f8fafc;border-bottom:1px solid #e5e7eb;">
                    <div style="font-size:18px;font-weight:800;color:#111827;display:flex;align-items:center;gap:8px;">
                        <span>📋</span>
                        <span>Тест таҳлили ва савол-жавоблар</span>
                    </div>
                    <button onclick="document.getElementById('attemptDetailModal').remove()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#6b7280;">&times;</button>
                </div>
                <div id="attemptDetailContent" style="padding:24px;overflow-y:auto;flex:1;">
                    <div style="text-align:center;padding:40px;color:#6b7280;font-weight:600;">
                        <div style="font-size:36px;margin-bottom:12px;">⏳</div>
                        Маълумотлар юкланмоқда...
                    </div>
                </div>
                <div style="padding:16px 24px;background:#f8fafc;border-top:1px solid #e5e7eb;text-align:right;">
                    <button id="downloadWordBtn" onclick="Employees.downloadWordReport()" style="margin-right:12px;padding:10px 24px;background:linear-gradient(135deg,#185abd,#104f9f);color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-size:13px;box-shadow:0 4px 12px rgba(24,90,189,0.3);transition:transform 0.15s;display:none;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">📥 Word (DOC)</button>
                    <button onclick="document.getElementById('attemptDetailModal').remove()" style="padding:10px 24px;background:#374151;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-size:13px;">Ёпиш</button>
                </div>
            </div>`;

        document.body.appendChild(modal);
        modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

        try {
            const params = {};
            if (empId && topicId) {
                params.emp_id = empId;
                params.topic_id = topicId;
                params.attempt_num = attemptNum;
            }
            const data = await API.getAttemptDetail(attemptId, params);
            const content = document.getElementById('attemptDetailContent');
            if (!content) return;

            if (data && data.error_msg) {
                content.innerHTML = `
                    <div style="padding:20px;background:#fee2e2;border:1px solid #fca5a5;border-radius:12px;color:#991b1b;font-family:monospace;white-space:pre-wrap;font-size:12px;margin:20px 0;text-align:left;line-height:1.4;">
                        <strong>SERVER ERROR:</strong> ${data.error_msg}
                        <hr style="border:0;border-top:1px solid #fca5a5;margin:10px 0;">
                        ${data.error_trace}
                    </div>`;
                return;
            }

            if (!data || !data.questions || data.questions.length === 0) {
                content.innerHTML = `<div style="text-align:center;padding:40px;color:#dc2626;font-weight:700;">Маълумот топилмади</div>`;
                return;
            }


            const isPassed = data.percentage >= 70;

            let html = `
                <!-- Subheader Info Card -->
                <div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);color:#fff;padding:20px 24px;border-radius:16px;margin-bottom:24px;box-shadow:0 6px 20px rgba(30,64,175,0.2);">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
                        <div>
                            <div style="font-size:18px;font-weight:800;">${data.employee_name || '—'}</div>
                            <div style="font-size:13px;opacity:0.85;margin-top:4px;">🏢 ${data.branch_name || '—'}</div>
                            <div style="font-size:13px;opacity:0.95;margin-top:6px;font-weight:600;color:#93c5fd;">📚 ${data.topic_name || '—'} (${data.attempt_number}-уриниш)</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="background:rgba(255,255,255,0.2);padding:6px 14px;border-radius:12px;font-size:14px;font-weight:800;display:inline-block;margin-bottom:6px;">
                                📊 ${data.score} / 15 (${data.percentage}%)
                            </div>
                            <div style="font-size:13px;opacity:0.9;font-weight:600;">⏱️ Вақт: ${data.duration}</div>
                        </div>
                    </div>
                </div>

                <!-- Questions List -->
                <div style="display:flex;flex-direction:column;gap:18px;">`;

            data.questions.forEach(q => {
                let badgeBg = '#dcfce7'; let badgeC = '#166534'; let badgeT = '✅ Тўғри';
                if (!q.is_correct) {
                    if (q.answer_status === 'TIMEOUT') {
                        badgeBg = '#ffedd5'; badgeC = '#c2410c'; badgeT = '⏱️ Вақт тугади';
                    } else {
                        badgeBg = '#fee2e2'; badgeC = '#991b1b'; badgeT = '❌ Нотоғри';
                    }
                }

                html += `
                <div style="border:1px solid #e5e7eb;border-radius:14px;padding:18px 20px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.03);">
                    <!-- Question Top Header -->
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #f3f4f6;">
                        <span style="font-size:13px;font-weight:800;color:#3b82f6;">📝 Савол ${q.display_order} / 15</span>
                        <div style="display:flex;align-items:center;gap:10px;">
                            <span style="font-size:12px;color:#6b7280;font-weight:600;">⏱️ ${q.response_time_sec} сония</span>
                            <span style="background:${badgeBg};color:${badgeC};padding:3px 10px;border-radius:12px;font-weight:700;font-size:11px;">${badgeT}</span>
                        </div>
                    </div>

                    <!-- Question Text -->
                    <div style="font-size:15px;font-weight:700;color:#111827;margin-bottom:14px;line-height:1.4;">
                        ${q.question_text || ''}
                    </div>

                    <!-- Options Grid -->
                    <div style="display:flex;flex-direction:column;gap:8px;">`;

                (q.options || []).forEach(opt => {
                    let optBg = '#f9fafb';
                    let optBorder = '1px solid #e5e7eb';
                    let optColor = '#374151';
                    let tag = '';

                    if (opt.is_selected && opt.is_correct) {
                        optBg = '#dcfce7';
                        optBorder = '2px solid #22c55e';
                        optColor = '#14532d';
                        tag = `<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:800;margin-left:auto;">👤 ✅ Ходим танлаган (Тўғри)</span>`;
                    } else if (opt.is_selected && !opt.is_correct) {
                        optBg = '#fee2e2';
                        optBorder = '2px solid #ef4444';
                        optColor = '#7f1d1d';
                        tag = `<span style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:800;margin-left:auto;">👤 ❌ Ходим танлаган (Нотоғри)</span>`;
                    } else if (!opt.is_selected && opt.is_correct) {
                        optBg = '#f0fdf4';
                        optBorder = '2px solid #86efac';
                        optColor = '#166534';
                        tag = `<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:800;margin-left:auto;">✅ Тўғри жавоб</span>`;
                    }

                    html += `
                        <div style="background:${optBg};border:${optBorder};color:${optColor};padding:10px 14px;border-radius:10px;font-size:13px;display:flex;align-items:center;gap:10px;font-weight:600;">
                            <span style="font-weight:800;font-size:12px;opacity:0.8;">${opt.label})</span>
                            <span style="flex:1;">${opt.text}</span>
                            ${tag}
                        </div>`;
                });

                html += `
                    </div>
                </div>`;
            });

            html += `</div>`;
            content.innerHTML = html;

            // Save data for Word export & show the Word button
            Employees.currentAttemptData = data;
            const wordBtn = document.getElementById('downloadWordBtn');
            if (wordBtn) wordBtn.style.display = 'inline-block';

        } catch (err) {
            const content = document.getElementById('attemptDetailContent');
            if (content) {
                content.innerHTML = `<div style="text-align:center;padding:40px;color:#dc2626;font-weight:700;">Хатолик: ${err.message}</div>`;
            }
        }
    },

    downloadWordReport() {
        const data = this.currentAttemptData;
        if (!data) return;

        let docHtml = `
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
        <head>
            <meta charset='utf-8'>
            <title>Тест натижалари - ${data.employee_name || ''}</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; color: #111827; }
                .header-card { background-color: #1e3a5f; color: #ffffff; padding: 20px; border-radius: 12px; margin-bottom: 24px; }
                .question-card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-bottom: 16px; background-color: #ffffff; }
                .question-header { font-size: 13px; font-weight: bold; color: #2563eb; border-bottom: 1px solid #f3f4f6; padding-bottom: 6px; margin-bottom: 8px; }
                .question-text { font-size: 14px; font-weight: bold; margin-bottom: 12px; }
                .option { padding: 8px 12px; border-radius: 8px; font-size: 12px; margin-bottom: 6px; font-weight: 600; display: block; }
                .correct { background-color: #dcfce7; border: 1px solid #22c55e; color: #14532d; }
                .incorrect { background-color: #fee2e2; border: 1px solid #ef4444; color: #7f1d1d; }
                .correct-hint { background-color: #f0fdf4; border: 1px solid #86efac; color: #166534; }
                .normal { background-color: #f9fafb; border: 1px solid #e5e7eb; color: #374151; }
                .badge { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; }
                .badge-success { background-color: #dcfce7; color: #166534; }
                .badge-danger { background-color: #fee2e2; color: #991b1b; }
                .badge-warning { background-color: #ffedd5; color: #c2410c; }
            </style>
        </head>
        <body>
            <div class="header-card">
                <h2 style="margin:0;">${data.employee_name || '—'}</h2>
                <p style="margin:4px 0 0 0;">🏢 Филиал: ${data.branch_name || '—'}</p>
                <p style="margin:4px 0 0 0;">📚 Мавзу: ${data.topic_name || '—'} (${data.attempt_number}-уриниш)</p>
                <p style="margin:10px 0 0 0;font-size:16px;font-weight:bold;">Натижа: ${data.score} / 15 (${data.percentage}%) | Вақт: ${data.duration}</p>
            </div>
            
            <h3 style="margin-bottom:16px;">Савол ва жавоблар таҳлили:</h3>
        `;

        data.questions.forEach(q => {
            let badgeText = '✅ Тўғри';
            let badgeClass = 'badge-success';
            if (!q.is_correct) {
                if (q.answer_status === 'TIMEOUT') {
                    badgeText = '⏱️ Вақт тугади';
                    badgeClass = 'badge-warning';
                } else {
                    badgeText = '❌ Нотоғри';
                    badgeClass = 'badge-danger';
                }
            }

            docHtml += `
            <div class="question-card">
                <div class="question-header">
                    Савол ${q.display_order} / 15 <span style="float:right;">⏱️ ${q.response_time_sec} сония | <span class="badge ${badgeClass}">${badgeText}</span></span>
                </div>
                <div class="question-text">${q.question_text || ''}</div>
                <div style="margin-top:8px;">
            `;

            (q.options || []).forEach(opt => {
                let optClass = 'normal';
                let suffix = '';
                if (opt.is_selected && opt.is_correct) {
                    optClass = 'correct';
                    suffix = ' [Ходим танлаган (Тўғри)]';
                } else if (opt.is_selected && !opt.is_correct) {
                    optClass = 'incorrect';
                    suffix = ' [Ходим танлаган (Нотоғри)]';
                } else if (!opt.is_selected && opt.is_correct) {
                    optClass = 'correct-hint';
                    suffix = ' [Тўғри жавоб]';
                }

                docHtml += `
                    <div class="option ${optClass}">
                        ${opt.label}) ${opt.text} ${suffix}
                    </div>
                `;
            });

            docHtml += `
                </div>
            </div>
            `;
        });

        docHtml += `
        </body>
        </html>
        `;

        const blob = new Blob(['\ufeff' + docHtml], { type: 'application/msword' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Test_Result_${data.employee_name.replace(/\s+/g, '_')}_Topic_${data.attempt_number}.doc`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};

