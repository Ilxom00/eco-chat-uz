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
            const s1 = t.attempt1 !== null && t.attempt1 !== undefined ? `<b>${t.attempt1}%</b>` : '<span style="color:#9ca3af;">—</span>';
            const s2 = t.attempt2 !== null && t.attempt2 !== undefined ? `<b>${t.attempt2}%</b>` : '<span style="color:#9ca3af;">—</span>';
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
    }
};
