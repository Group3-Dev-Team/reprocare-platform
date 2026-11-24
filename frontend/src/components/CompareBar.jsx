import { facilityDisplayName } from '../data/facilityNames';
import { Link, useLocation } from 'react-router-dom';
import { Columns3, X } from 'lucide-react';
import { useCompare } from '../hooks/useCompare';

/** Sticky tray that appears once a visitor picks facilities to compare. */
export function CompareBar() {
  const { items, toggle, clear } = useCompare();
  const { pathname } = useLocation();
  if (!items.length || pathname === '/compare') return null;
  return (
    <div className="compare-bar" role="region" aria-label="Facilities to compare">
      <div className="container compare-bar-inner">
        <span className="compare-tray-count">
          <Columns3 size={18} aria-hidden="true" />
          <span aria-live="polite">{items.length} selected</span>
        </span>
        <ul className="compare-chips">
          {items.map((item) => (
            <li key={item.slug}>
              {facilityDisplayName(item)}
              <button aria-label={`Remove ${facilityDisplayName(item)}`} onClick={() => toggle(item)}>
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
        <div className="row" style={{ marginLeft: 'auto' }}>
          <button className="btn btn-ghost btn-sm compare-clear" onClick={clear}>
            Clear
          </button>
          <Link to="/compare" className="btn btn-primary btn-sm">
            Compare {items.length === 1 ? 'facility' : 'facilities'}
          </Link>
        </div>
      </div>
    </div>
  );
}
