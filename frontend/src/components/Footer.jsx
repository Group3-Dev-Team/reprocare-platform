import { Link } from 'react-router-dom';
import { ArrowUp, MessageCircle, Phone } from 'lucide-react';
import { footerNav } from '../data/navigation';
import { Logo } from './Logo';

const whatsappNumber = (import.meta.env.VITE_WHATSAPP_SUPPORT_NUMBER || '').trim();
const supportLink = /^\+?[1-9]\d{7,14}$/.test(whatsappNumber)
  ? 'https://wa.me/' + whatsappNumber.replace(/^\+/, '')
  : null;

function backToTop() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.getElementById('main')?.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: reduceMotion ? 'instant' : 'smooth' });
}

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-emergency" role="note">
          <Phone size={18} aria-hidden="true" />
          <p>
            <strong>In an emergency</strong> go to the nearest health facility or call <a href="tel:999">999</a> or <a href="tel:112">112</a>. ReproCare is an information service and
            cannot respond to emergencies.
          </p>
        </div>
        <div className="footer-grid">
          <div className="footer-brand">
            <Logo />
            <p>Independent reproductive healthcare discovery for Kenya.</p>
          </div>
          {footerNav.map((group) => (
            <nav key={group.heading} aria-label={group.heading} className="footer-col">
              <h2>{group.heading}</h2>
              <ul>
                {group.links.map((link) => (
                  <li key={link.to}>
                    <Link to={link.to}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <div className="footer-base">
          <button className="btn btn-secondary btn-sm back-to-top" type="button" onClick={backToTop}>
            <ArrowUp size={16} aria-hidden="true" /> Back to top
          </button>
          <p>© {new Date().getFullYear()} ReproCare. Information on this site is general and does not replace advice from a qualified health worker.</p>
          <p>
            Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>
          </p>
        </div>
      </div>
      {supportLink && (
        <a className="support-contact icon-btn" href={supportLink} target="_blank" rel="noopener noreferrer"
          aria-label="Contact ReproCare on WhatsApp (opens in a new tab)">
          <MessageCircle size={22} aria-hidden="true" />
        </a>
      )}
    </footer>
  );
}
