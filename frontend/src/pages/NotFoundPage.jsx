import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { EmptyState } from '../components/Feedback';

export default function NotFoundPage({ what = 'page' }) {
  useDocumentTitle('Not found', 'ReproCare could not find this page.', { noIndex: true });
  return (
    <div className="container section">
      <EmptyState
        titleAs="h1"
        icon={<Compass size={26} />}
        title={`We could not find that ${what}`}
        action={
          <div className="row" style={{ justifyContent: 'center' }}>
            <Link className="btn btn-primary" to="/find-care/facilities">Find care</Link>
            <Link className="btn btn-secondary" to="/">Go to the homepage</Link>
          </div>
        }
      >
        The link may be out of date, or the {what} may have been removed.
      </EmptyState>
    </div>
  );
}
