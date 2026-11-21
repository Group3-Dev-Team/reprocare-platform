import { useEffect } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { formatDate } from '../../data/labels';
import { DashboardHeader } from '../../components/DashboardParts';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';

export default function Notifications() {
  useDocumentTitle('Notifications');
  const { setUnread } = useOutletContext();
  const result = useFetch(() => api.notifications(), []);

  useEffect(() => {
    if (result.data?.unread) api.markNotificationsRead().then(() => setUnread(0)).catch(() => {});
  }, [result.data, setUnread]);

  return (
    <>
      <DashboardHeader title="Notifications" description="Updates about your requests, registrations and reviews." />
      {result.loading && <LoadingState rows={3} height={70} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.items.length === 0 && <EmptyState icon={<Bell size={24} />} title="No notifications yet">We will let you know here when a facility answers a request or a review is published.</EmptyState>}
      <ul className="notification-list">
        {(result.data?.items || []).map((n) => (
          <li key={n.id} className={n.is_read ? '' : 'is-unread'}>
            <span className="notification-dot" aria-hidden="true" />
            <div>
              <strong>{n.title}</strong>
              {n.body && <p>{n.body}</p>}
              <span className="small muted">{formatDate(n.created_at, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            {n.link && <Link to={n.link} className="btn btn-ghost btn-sm">Open</Link>}
          </li>
        ))}
      </ul>
    </>
  );
}
