import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useFetch } from '../hooks/useFetch';
import { request } from '../services/api';

export default function HomePage() {
  useDocumentTitle('Find reproductive care in Kenya');
  const health = useFetch((signal) => request('GET', '/health', { signal, anonymous: true }), []);
  return (
    <section className="container section stack">
      <h1>ReproCare</h1>
      <p className="muted">Shared application foundation. Feature pages are added by their workstreams.</p>
      <p className="small" role="status">API: {health.loading ? 'checking…' : health.error ? 'not reachable' : 'connected'}</p>
    </section>
  );
}
