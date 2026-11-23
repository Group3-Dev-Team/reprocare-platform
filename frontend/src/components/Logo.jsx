import { Link } from 'react-router-dom';
import logo from '../assets/reprocare-logo.svg';

/** The ReproCare mark and wordmark. Replace src/assets/reprocare-logo.svg to change it everywhere. */
export function Logo({ light = false, to = '/' }) {
  return (
    <Link to={to} className={`logo ${light ? 'logo-light' : ''}`} aria-label="ReproCare home">
      <img src={logo} alt="" width="34" height="31" />
      <span className="logo-text">
        <span className="logo-word">ReproCare</span>
        <span className="logo-tag">Find. Compare. Trust.</span>
      </span>
    </Link>
  );
}
