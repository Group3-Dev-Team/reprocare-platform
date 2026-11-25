import { Link } from 'react-router-dom';
import { Globe, Mail, Navigation, Phone } from 'lucide-react';
import { facilityDisplayName } from '../data/facilityNames';
import { Modal } from './Modal';

/**
 * "Book appointment" for a facility that does not take requests through ReproCare: says so plainly and offers
 * only the contact routes the listing actually has. Nothing here suggests ReproCare availability.
 */
export function BookingContactModal({ facility, website, directions, onClose }) {
  const name = facilityDisplayName(facility);
  const phone = facility.phone?.trim();
  const email = facility.email?.trim();
  const hasContact = Boolean(phone || email || website);
  return (
    <Modal title="Book an appointment" description={name} onClose={onClose}
      footer={<button className="btn btn-secondary" onClick={onClose}>Close</button>}>
      <p>
        {name} does not take appointment requests through ReproCare yet.{' '}
        {hasContact ? 'Contact the facility directly to book a visit:' : 'No booking contact details are listed for this facility yet.'}
      </p>
      <div className="row">
        {phone && (
          <a className="btn btn-primary" href={`tel:${phone.replace(/\s/g, '')}`}>
            <Phone size={17} aria-hidden="true" /> Call {phone}
          </a>
        )}
        {email && (
          <a className="btn btn-secondary" href={`mailto:${email}`}>
            <Mail size={17} aria-hidden="true" /> Email
          </a>
        )}
        {website && (
          <a className="btn btn-secondary" href={website} target="_blank" rel="noopener noreferrer">
            <Globe size={17} aria-hidden="true" /> Facility website
          </a>
        )}
        {directions && (
          <a className="btn btn-ghost" href={directions} target="_blank" rel="noreferrer">
            <Navigation size={17} aria-hidden="true" /> Directions
          </a>
        )}
      </div>
      <p className="small muted">
        Facilities marked “Accepts ReproCare requests” take booking requests online.{' '}
        <Link to="/find-care/facilities?accepts_requests=true" onClick={onClose}>Find participating facilities</Link>
      </p>
    </Modal>
  );
}
