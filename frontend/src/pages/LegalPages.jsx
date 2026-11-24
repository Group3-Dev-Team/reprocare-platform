import { Link } from 'react-router-dom';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/PageHeader';
import { Alert } from '../components/Feedback';

const draftNote = (
  <Alert tone="warning" title="Draft for review">
    <p>This text describes how the current software handles information. It must be reviewed against the Kenya Data Protection Act, 2019 by a qualified adviser before ReproCare goes live.</p>
  </Alert>
);

export function PrivacyPage() {
  useDocumentTitle('Privacy notice');
  return (
    <>
      <PageHeader title="Privacy notice" intro="What ReproCare collects, why, and the choices you have." crumbs={[{ label: 'Privacy notice' }]} />
      <div className="container section-sm">
        <article className="article prose">
          {draftNote}
          <h2>Browsing without an account</h2>
          <p>You can search, read and compare without signing in. We do not ask for your name to browse, and your searches are not linked to you.</p>
          <h2>What we keep when you create an account</h2>
          <ul>
            <li>Your name, email address and, if you add it, phone number.</li>
            <li>Facilities you save, appointment requests you send, programmes you register for, reviews you write and notifications we send you.</li>
            <li>A record of your sign-in sessions so you can stay signed in. Signing out deletes the session.</li>
          </ul>
          <h2>Who sees what</h2>
          <ul>
            <li>A facility sees the appointment requests sent to it, including your name, email, phone number and note. It does not see your other activity.</li>
            <li>A programme organiser sees the name and phone number you give when registering.</li>
            <li>Published reviews show your first name and the initial of your surname.</li>
            <li>ReproCare administrators can see account and moderation records when they need to support you.</li>
          </ul>
          <h2>What we never do</h2>
          <p>We do not sell personal information or search histories, and we do not collect medical records. Please do not put medical details in free-text fields.</p>
          <h2>Your choices</h2>
          <p>You can update your name and phone number in your account settings at any time. To ask for a copy of your information or for your account to be deleted, <Link to="/contact?topic=privacy">send a privacy request</Link>.</p>
        </article>
      </div>
    </>
  );
}

export function TermsPage() {
  useDocumentTitle('Terms of use');
  return (
    <>
      <PageHeader title="Terms of use" intro="The basic rules for using ReproCare." crumbs={[{ label: 'Terms of use' }]} />
      <div className="container section-sm">
        <article className="article prose">
          {draftNote}
          <h2>Information, not medical advice</h2>
          <p>ReproCare provides general information to help you find and compare healthcare. It does not diagnose, prescribe or replace a qualified health worker. In an emergency call 999 or 112.</p>
          <h2>Accuracy of listings</h2>
          <p>Each detail is labelled with its source. Facilities change their services, hours and arrangements, so confirm important details with the facility before you travel.</p>
          <h2>Appointment requests</h2>
          <p>A request sent through ReproCare is not an appointment until the facility confirms it. Facilities decide whether and when they can see you.</p>
          <h2>Reviews</h2>
          <p>Write only about your own experience. Do not include names, contact details or medical information. Moderators may decline reviews that break these rules.</p>
          <h2>Accounts</h2>
          <p>Keep your password private. We may suspend accounts that misuse the service, for example by posting false reviews or making repeated false requests.</p>
        </article>
      </div>
    </>
  );
}
