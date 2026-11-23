import { useState } from 'react';
import { Link } from 'react-router-dom';
import { MAX_PLAN_FACILITIES, readCarePlan, writeCarePlan } from '../data/careplan';

export function PlanFacilityButton({ slug }) {
  const [added, setAdded] = useState(() => readCarePlan().facilities.includes(slug));
  const [error, setError] = useState('');

  const toggle = () => {
    const current = readCarePlan();
    const saved = current.facilities.includes(slug);
    if (!saved && current.facilities.length >= MAX_PLAN_FACILITIES) {
      setError('Your care plan has six facilities. Remove one before adding another.');
      return;
    }

    const facilities = saved
      ? current.facilities.filter((item) => item !== slug)
      : [...current.facilities, slug];
    if (!writeCarePlan({ ...current, facilities })) {
      setError('Your browser could not save this facility to the care plan.');
      return;
    }

    setError('');
    setAdded(!saved);
  };

  return (
    <div className="stack">
      <div className="row">
        <button type="button" className="btn btn-secondary btn-sm" aria-label="Add facility to this tab’s care plan"
          aria-pressed={added} onClick={toggle}>
          {added ? 'Added to care plan' : 'Add to care plan'}
        </button>
        {added && <Link to="/care-planner" className="small">Open care planner</Link>}
      </div>
      {error && <p className="small" role="status">{error}</p>}
    </div>
  );
}
