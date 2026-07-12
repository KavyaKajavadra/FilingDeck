/* ═══════════════════════════════════════════════════════════════════════════
   FilingDeck — Visual Compliance Calendar
   Renders monthly calendar grids with clickable deadline dates
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('calendarContainer');
    const modal = document.getElementById('calendarModal');
    const modalClose = document.getElementById('modalClose');
    const modalDate = document.getElementById('modalDate');
    const modalContent = document.getElementById('modalContent');

    if (!container || !window.DEADLINE_DATA) return;
    
    const DEADLINE_DATA = window.DEADLINE_DATA;

    const MONTHS = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    // ── Group deadlines by date ─────────────────────────────────────────
    const deadlineMap = {};
    DEADLINE_DATA.forEach(d => {
        const dateKey = d.due_date; // "YYYY-MM-DD"
        if (!deadlineMap[dateKey]) {
            deadlineMap[dateKey] = [];
        }
        deadlineMap[dateKey].push(d);
    });

    // ── Determine which months to render ────────────────────────────────
    const today = new Date();
    const monthsToShow = 6;
    const monthList = [];

    for (let i = 0; i < monthsToShow; i++) {
        const d = new Date(today.getFullYear(), today.getMonth() + i, 1);
        monthList.push({ year: d.getFullYear(), month: d.getMonth() });
    }

    // ── Render all month grids ──────────────────────────────────────────
    monthList.forEach(({ year, month }) => {
        const monthEl = createMonthGrid(year, month);
        container.appendChild(monthEl);
    });

    // ── Create a single month calendar grid ─────────────────────────────
    function createMonthGrid(year, month) {
        const wrapper = document.createElement('div');
        wrapper.className = 'calendar-month';

        // Month header
        const header = document.createElement('div');
        header.className = 'calendar-month-header';
        header.innerHTML = `
            <h3>${MONTHS[month]} ${year}</h3>
            <span class="calendar-month-count">${countDeadlinesInMonth(year, month)} filings</span>
        `;
        wrapper.appendChild(header);

        // Day labels row
        const dayLabels = document.createElement('div');
        dayLabels.className = 'calendar-grid calendar-day-labels';
        DAYS.forEach(day => {
            const label = document.createElement('div');
            label.className = 'calendar-day-label';
            label.textContent = day;
            dayLabels.appendChild(label);
        });
        wrapper.appendChild(dayLabels);

        // Calendar grid
        const grid = document.createElement('div');
        grid.className = 'calendar-grid';

        // First day of month
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Empty cells for days before first of month
        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement('div');
            empty.className = 'calendar-cell empty';
            grid.appendChild(empty);
        }

        // Day cells
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const cell = document.createElement('div');
            cell.className = 'calendar-cell';

            const isToday = (
                day === today.getDate() &&
                month === today.getMonth() &&
                year === today.getFullYear()
            );

            if (isToday) cell.classList.add('today');

            const deadlines = deadlineMap[dateStr];
            if (deadlines && deadlines.length > 0) {
                // Get the most urgent status
                const urgency = getMostUrgentStatus(deadlines);
                cell.classList.add('has-deadline', urgency);

                // Day number
                const dayNum = document.createElement('span');
                dayNum.className = 'cell-day';
                dayNum.textContent = day;
                cell.appendChild(dayNum);

                // Deadline dots / indicators
                const dotsContainer = document.createElement('div');
                dotsContainer.className = 'cell-dots';

                // Show up to 3 dots for deadlines
                const maxDots = Math.min(deadlines.length, 3);
                for (let i = 0; i < maxDots; i++) {
                    const dot = document.createElement('span');
                    dot.className = `cell-dot ${deadlines[i].status}`;
                    dotsContainer.appendChild(dot);
                }
                if (deadlines.length > 3) {
                    const more = document.createElement('span');
                    more.className = 'cell-more';
                    more.textContent = `+${deadlines.length - 3}`;
                    dotsContainer.appendChild(more);
                }
                cell.appendChild(dotsContainer);

                // Short label (first deadline name, truncated)
                const label = document.createElement('span');
                label.className = 'cell-label';
                label.textContent = deadlines[0].name;
                cell.appendChild(label);

                // Click handler
                cell.addEventListener('click', () => showDeadlineDetails(dateStr, deadlines));
                cell.style.cursor = 'pointer';
            } else {
                const dayNum = document.createElement('span');
                dayNum.className = 'cell-day';
                dayNum.textContent = day;
                cell.appendChild(dayNum);
            }

            grid.appendChild(cell);
        }

        wrapper.appendChild(grid);
        return wrapper;
    }

    // ── Count deadlines in a month ──────────────────────────────────────
    function countDeadlinesInMonth(year, month) {
        let count = 0;
        Object.keys(deadlineMap).forEach(dateStr => {
            const d = new Date(dateStr);
            if (d.getFullYear() === year && d.getMonth() === month) {
                count += deadlineMap[dateStr].length;
            }
        });
        return count;
    }

    // ── Get the most urgent status from a list of deadlines ─────────────
    function getMostUrgentStatus(deadlines) {
        const priority = ['overdue', 'critical', 'urgent', 'upcoming', 'safe'];
        let most = 'safe';
        for (const d of deadlines) {
            if (priority.indexOf(d.status) < priority.indexOf(most)) {
                most = d.status;
            }
        }
        return most;
    }

    // ── Show detail modal ───────────────────────────────────────────────
    function showDeadlineDetails(dateStr, deadlines) {
        const dateObj = new Date(dateStr + 'T00:00:00');
        const formatted = dateObj.toLocaleDateString('en-IN', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });

        modalDate.textContent = formatted;

        let html = '';
        deadlines.forEach(d => {
            const statusLabel = {
                safe: '✅ Safe',
                upcoming: '🔵 Upcoming',
                urgent: '🟡 Urgent',
                critical: '🔴 Critical',
                overdue: '⛔ Overdue'
            };

            html += `
                <div class="modal-deadline-item">
                    <div class="modal-deadline-header">
                        <span class="modal-category">${d.category}</span>
                        <span class="modal-status ${d.status}">${statusLabel[d.status] || d.status}</span>
                    </div>
                    <h3 class="modal-filing-name">${d.name}</h3>
                    <p class="modal-filing-desc">${d.description}</p>
                    <div class="modal-meta">
                        <div class="modal-meta-item">
                            <span class="modal-meta-label">Filing Period</span>
                            <span class="modal-meta-value">${d.period}</span>
                        </div>
                        <div class="modal-meta-item">
                            <span class="modal-meta-label">Days Left</span>
                            <span class="modal-meta-value ${d.status}">
                                ${d.days_left === null ? 'See details' :
                                  d.days_left === 0 ? 'Due today!' :
                                  d.days_left < 0 ? Math.abs(d.days_left) + ' days overdue' :
                                  d.days_left + ' days'}
                            </span>
                        </div>
                    </div>
                    <div class="modal-penalty">
                        <span class="modal-penalty-icon">⚠️</span>
                        <span>${d.penalty_info}</span>
                    </div>
                </div>
            `;
        });

        modalContent.innerHTML = html;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    // ── Close modal ─────────────────────────────────────────────────────
    modalClose.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    function closeModal() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
});
