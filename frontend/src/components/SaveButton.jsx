import { facilityDisplayName } from '../data/facilityNames';
import { Heart } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useSaved } from '../hooks/useSaved';
import { useToast } from './Toast';

/** Heart toggle. Visitors are sent to sign in first; only patient accounts can save. */
export function SaveButton({ facility, withLabel = false }) {
  const { user } = useAuth();
  const { isSaved, toggle } = useSaved();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  if (user && user.role !== 'patient') return null;
  const saved = isSaved(facility.slug);

  const onClick = async () => {
    if (!user) {
      navigate(`/sign-in?next=${encodeURIComponent(location.pathname)}`);
      return;
    }
    try {
      const nowSaved = await toggle(facility.slug);
      toast(nowSaved ? `${facilityDisplayName(facility)} saved to your list` : `${facilityDisplayName(facility)} removed from your list`);
    } catch (error) {
      toast(error.message, 'error');
    }
  };

  if (withLabel) {
    return (
      <button className="btn btn-secondary" aria-pressed={saved} onClick={onClick}>
        <Heart size={17} fill={saved ? 'var(--rose-500)' : 'none'} color={saved ? 'var(--rose-600)' : 'currentColor'} aria-hidden="true" />
        {saved ? 'Saved' : 'Save'}
      </button>
    );
  }
  return (
    <button className="icon-btn" aria-pressed={saved} aria-label={saved ? `Remove ${facilityDisplayName(facility)} from saved` : `Save ${facilityDisplayName(facility)}`} onClick={onClick}>
      <Heart size={18} fill={saved ? 'currentColor' : 'none'} />
    </button>
  );
}
