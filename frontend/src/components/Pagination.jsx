/** Page controls plus a "Showing 41–80 of 123" count. */
export function Pagination({ page, pages, total, pageSize, onChange, noun = 'results', showSummary = true }) {
  if (!total) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  const numbers = [];
  for (let n = 1; n <= pages; n += 1) {
    if (n === 1 || n === pages || Math.abs(n - page) <= 1) numbers.push(n);
    else if (numbers[numbers.length - 1] !== '…') numbers.push('…');
  }
  return (
    <nav className="pagination" aria-label="Pagination">
      {showSummary && (
        <p className="small muted" style={{ margin: 0 }}>
          Showing <strong>{from}</strong>–<strong>{to}</strong> of <strong>{total}</strong> {noun}
        </p>
      )}
      {pages > 1 && (
        <div className="pagination-pages">
          <button className="page-btn" disabled={page === 1} onClick={() => onChange(page - 1)}>
            Previous
          </button>
          {numbers.map((n, i) =>
            n === '…' ? (
              <span key={`gap${i}`} className="page-btn" aria-hidden="true" style={{ border: 0, background: 'none' }}>
                …
              </span>
            ) : (
              <button key={n} className="page-btn" aria-current={n === page ? 'page' : undefined} onClick={() => onChange(n)}>
                {n}
              </button>
            ),
          )}
          <button className="page-btn" disabled={page === pages} onClick={() => onChange(page + 1)}>
            Next
          </button>
        </div>
      )}
    </nav>
  );
}
