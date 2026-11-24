import { useId, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { nairobiToday } from '../data/agenda';
import { formatDate } from '../data/labels';

const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const fullDate = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
const monthTitle = { month: 'long', year: 'numeric' };

function moveMonth(month, offset) {
  const date = new Date(month + '-01T00:00:00Z');
  date.setUTCMonth(date.getUTCMonth() + offset);
  return date.toISOString().slice(0, 7);
}

function daysOfMonth(month) {
  const first = new Date(month + '-01T00:00:00Z');
  const blankDays = (first.getUTCDay() + 6) % 7;
  const next = new Date(moveMonth(month, 1) + '-01T00:00:00Z');
  const last = new Date(next.getTime() - 86_400_000).getUTCDate();
  const cellCount = Math.ceil((blankDays + last) / 7) * 7;
  const cells = Array.from({ length: cellCount }, (_, index) => {
    const day = index - blankDays + 1;
    return day >= 1 && day <= last ? month + '-' + String(day).padStart(2, '0') : null;
  });
  return Array.from({ length: cellCount / 7 }, (_, index) => cells.slice(index * 7, (index + 1) * 7));
}

export function AppointmentCalendar({ items, children, partial = false }) {
  const today = nairobiToday();
  const currentMonth = today.slice(0, 7);
  const [month, setMonth] = useState(currentMonth);
  const [selectedDate, setSelectedDate] = useState(null);
  const titleId = useId();
  const title = formatDate(month + '-01', monthTitle);
  const monthItems = items.filter(({ date }) => date.slice(0, 7) === month);
  const counts = new Map();
  for (const { date } of monthItems) counts.set(date, (counts.get(date) || 0) + 1);
  const visible = selectedDate ? monthItems.filter(({ date }) => date === selectedDate) : monthItems;
  const nextDate = items.find(({ date }) => date.slice(0, 7) > month);
  const noun = visible.length === 1 ? 'entry' : 'entries';
  const scope = selectedDate ? formatDate(selectedDate, fullDate) : title;

  const openMonth = (value) => {
    setMonth(value);
    setSelectedDate(null);
  };

  return (
    <div className="stack appointments-calendar">
      <section className="panel stack" aria-labelledby={titleId}>
        <div className="spread calendar-month-heading">
          <h2 id={titleId}>{title}</h2>
          <div className="row calendar-month-actions">
            <button type="button" className="btn btn-secondary btn-sm" aria-label="Previous month"
              disabled={month <= currentMonth} onClick={() => openMonth(moveMonth(month, -1))}>
              <ChevronLeft size={17} aria-hidden="true" />
            </button>
            <button type="button" className="btn btn-secondary btn-sm" disabled={month === currentMonth}
              onClick={() => openMonth(currentMonth)}>This month</button>
            <button type="button" className="btn btn-secondary btn-sm" aria-label="Next month"
              onClick={() => openMonth(moveMonth(month, 1))}>
              <ChevronRight size={17} aria-hidden="true" />
            </button>
          </div>
        </div>
        <table className="calendar-month-table">
          <caption className="sr-only">Dates in {title}</caption>
          <thead>
            <tr>{weekdays.map((day) => <th key={day} scope="col"><span className="sr-only">{day}</span><span aria-hidden="true">{day.slice(0, 3)}</span></th>)}</tr>
          </thead>
          <tbody>
            {daysOfMonth(month).map((week, index) => (
              <tr key={index}>
                {week.map((date, column) => {
                  const count = counts.get(date);
                  const day = date && Number(date.slice(-2));
                  const todayAttribute = date === today ? 'date' : undefined;
                  return (
                    <td key={column}>
                      {count ? (
                        <button type="button" className="calendar-day" aria-current={todayAttribute} aria-pressed={date === selectedDate}
                          aria-label={formatDate(date, fullDate) + ', ' + count + (count === 1 ? ' entry' : ' entries')}
                          onClick={() => setSelectedDate(date === selectedDate ? null : date)}>
                          {day}<span className="calendar-day-count" aria-hidden="true">{count}</span>
                        </button>
                      ) : date ? <time className="calendar-day" dateTime={date} aria-current={todayAttribute}>{day}</time> : null}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {selectedDate && (
          <button type="button" className="btn btn-secondary btn-sm calendar-month-return" onClick={() => setSelectedDate(null)}>
            Show whole month
          </button>
        )}
        {!monthItems.length && nextDate && (
          <button type="button" className="btn btn-secondary btn-sm calendar-month-return" onClick={() => openMonth(nextDate.date.slice(0, 7))}>
            Open next month with entries
          </button>
        )}
      </section>
      <p className="small muted" role="status">{visible.length} {partial && 'loaded '}{noun} for {scope}.</p>
      {children(visible)}
    </div>
  );
}
