import { useEffect, useState } from 'react';
import { MessagesSquare } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { DashboardHeader, Tabs } from '../../components/DashboardParts';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import { Pagination } from '../../components/Pagination';
import { Select, TextInput } from '../../components/Forms';
import { formatDate } from '../../data/labels';

const TABS = [
  { value: 'all', label: 'All Posts' },
  { value: 'pending', label: 'Awaiting review' },
  { value: 'published', label: 'Published' },
  { value: 'withheld', label: 'Withheld' },
];

const COLLECTION_TIME = {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  timeZone: 'Africa/Nairobi', timeZoneName: 'short',
};

function postStatus(post) {
  if (post.published) return 'Published';
  if (post.previously_visible) return 'Previously visible · Awaiting attribution';
  return post.status === 'withheld' ? 'Withheld' : 'Awaiting review';
}

function CollectionTime({ value }) {
  return value && <span>Collected <time dateTime={value}>{formatDate(value, COLLECTION_TIME)}</time></span>;
}

function CollectedComments({ post }) {
  const comments = new Map(post.comments.map((comment) => [comment.id, comment]));
  const states = {
    visible: post.published ? 'Selected for publication' : 'Collected',
    held: 'Held',
    hidden: 'Hidden',
  };

  return (
    <>
      <h3>Stored comments and replies ({post.comments.length.toLocaleString()})</h3>
      {post.comments.length === 0 ? <p>No comments have been collected for this post.</p> : (
        <ul className="stack">
          {post.comments.map((comment) => {
            const parent = comments.get(comment.parent_id);
            return (
              <li key={comment.id} id={`facebook-comment-${comment.id}`}>
                <strong>{comment.author || 'Facebook user'}</strong>
                {parent && <> · Reply to <a href={`#facebook-comment-${parent.id}`}>{parent.author || 'Facebook user'}</a></>}
                {!parent && comment.parent_id != null && <> · Reply to comment #{comment.parent_id}</>}
                <p className="xc-text">{comment.text}</p>
                <p className="small muted">
                  {states[comment.status]}
                  {comment.collected_at && <> · <CollectionTime value={comment.collected_at} /></>}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

function DecisionForm({ post, onSaved, onConflict }) {
  const [scope, setScope] = useState(post.scope || '');
  const [note, setNote] = useState(post.note || '');
  const [selected, setSelected] = useState(() => post.published
    ? post.comments.filter((comment) => comment.status === 'visible').map((comment) => comment.id)
    : []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const comments = new Map(post.comments.map((comment) => [comment.id, comment]));

  const toggle = (comment, checked) => setSelected((current) => checked
    ? [...current, comment.id]
    : current.filter((id) => id !== comment.id && comments.get(id)?.parent_id !== comment.id));

  const save = async (decision) => {
    setSaving(true);
    setError(null);
    try {
      await api.moderateFacebookPost(post.id, {
        decision,
        scope: scope || null,
        note,
        comment_ids: selected,
        reviewed_at: post.reviewed_at,
      });
      onSaved(decision);
    } catch (failure) {
      setError(failure);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <p>Check the original context and branch attribution. A shared page may support organization-level feedback. Select only comments appropriate for public display.</p>
      <form className="stack" onSubmit={(event) => { event.preventDefault(); save('publish'); }}>
        <fieldset disabled={saving} className="stack">
          <label>
            Attribution
            <select className="select" value={scope} onChange={(event) => setScope(event.target.value)}>
              <option value="">Choose attribution</option>
              <option value="facility">Specific to this facility</option>
              <option value="organization">Organization-level</option>
            </select>
          </label>
          <label>
            Internal decision note
            <textarea className="input" value={note} maxLength={2000} onChange={(event) => setNote(event.target.value)} />
          </label>
          <fieldset className="stack">
            <legend>Comments to publish</legend>
            {post.comments.map((comment) => {
              const parent = comments.get(comment.parent_id);
              const blocked = comment.status === 'hidden' || (comment.parent_id != null
                && (!parent || parent.parent_id != null || !selected.includes(parent.id)));
              return (
                <label key={comment.id}>
                  <input type="checkbox" checked={selected.includes(comment.id)} disabled={blocked}
                    onChange={(event) => toggle(comment, event.target.checked)} />
                  {comment.parent_id != null ? ' Reply · ' : ' '}
                  {comment.author} · <span className="xpost-caption">{comment.text}</span>
                  {comment.screening && <span className="small muted"> · {comment.screening}</span>}
                  {comment.status === 'hidden' && <span className="small muted"> · Hidden</span>}
                </label>
              );
            })}
          </fieldset>
          <div className="moderation-actions">
            <button type="submit" className="btn btn-success btn-sm"
              disabled={!scope || !note.trim() || !selected.length || !post.source_url || !post.facility}>Publish selected feedback</button>
            <button type="button" className="btn btn-secondary btn-sm" disabled={!note.trim()}
              onClick={() => save('withhold')}>Withhold post</button>
          </div>
        </fieldset>
      </form>
      {error && <ErrorState error={error} onRetry={error.status === 409 ? onConflict : undefined} />}
    </>
  );
}

function PostReview({ id, onSaved }) {
  const [moderating, setModerating] = useState(false);
  const detail = useFetch((signal) => api.adminFacebookPost(id, { signal }), [id]);
  if (detail.loading) return <LoadingState rows={2} />;
  if (detail.error) return <ErrorState error={detail.error} onRetry={detail.reload} />;
  const post = detail.data;

  return (
    <div className="panel stack">
      <h2>{post.facility || 'Unlinked facility'}</h2>
      <p className="small muted">
        {post.page ? `Facebook · @${post.page}` : 'Facebook'}
        {post.collected_at && <> · <CollectionTime value={post.collected_at} /></>}
      </p>
      {post.source_url && <a href={post.source_url} target="_blank" rel="noopener noreferrer nofollow">Open original Facebook post</a>}
      {post.previously_visible && <p>This post was previously visible and requires attribution review.</p>}
      {post.caption && <p className="xpost-caption">{post.caption}</p>}
      <h3>Stored Facebook profiles</h3>
      {post.profiles.length ? <ul>{post.profiles.map((profile, index) => (
        <li key={index}>
          {profile.facility} · {profile.page ? `@${profile.page}` : 'Page unavailable'} · {profile.match_method}
          {profile.page_matches ? ' · Matches post URL' : ''}
        </li>
      ))}</ul> : <p>No matching profile is stored.</p>}
      <div className="row">
        <button type="button" className="btn btn-secondary btn-sm" aria-expanded={moderating}
          onClick={() => setModerating(!moderating)}>
          {moderating ? 'Back to stored comments' : 'Review for publication'}
        </button>
      </div>
      {moderating ? <DecisionForm post={post} onSaved={onSaved} onConflict={detail.reload} /> : <CollectedComments post={post} />}
    </div>
  );
}

export default function AdminFacebookFeedback() {
  useDocumentTitle('Collected Facebook Feedback');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(1);
  const [facilities, setFacilities] = useState([]);
  const [facilityId, setFacilityId] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState('');
  const queue = useFetch((signal) => api.adminFacebookPosts({ status, page, facility_id: facilityId, q: query }, { signal }),
    [status, page, facilityId, query]);

  useEffect(() => {
    if (queue.data?.facilities) setFacilities(queue.data.facilities);
  }, [queue.data]);

  const resetPage = () => {
    setPage(1);
    setSelected(null);
  };

  const saved = (decision) => {
    setMessage(decision === 'publish' ? 'Selected Facebook feedback was published.' : 'Facebook post was withheld.');
    setSelected(null);
    if (status !== 'all' && page > 1 && queue.data?.items.length === 1 && status !== (decision === 'publish' ? 'published' : 'withheld')) {
      setPage(page - 1);
    } else {
      queue.reload();
    }
  };

  return (
    <>
      <DashboardHeader title="Collected Facebook Feedback" description="Inspect collected posts and comments, including unpublished material. Publication decisions are made separately." />
      <Tabs value={status} options={TABS} onChange={(value) => { setStatus(value); resetPage(); }} />
      <form className="form-grid" onSubmit={(event) => { event.preventDefault(); setQuery(searchInput.trim()); resetPage(); }}>
        <Select label="Facility" placeholder="All facilities" value={facilityId}
          options={facilities.map((facility) => ({ value: facility.id, label: facility.name }))}
          onChange={(event) => { setFacilityId(event.target.value); resetPage(); }} />
        <TextInput type="search" label="Search posts" value={searchInput} maxLength={100}
          onChange={(event) => setSearchInput(event.target.value)} />
        <div className="span-2 row">
          <button type="submit" className="btn btn-secondary btn-sm">Search</button>
        </div>
      </form>
      {message && <p role="status">{message}</p>}
      {queue.loading && <LoadingState rows={2} />}
      {queue.error && <ErrorState error={queue.error} onRetry={queue.reload} />}
      {!queue.loading && queue.data && (
        <p className="small muted" aria-live="polite">
          {queue.data.total.toLocaleString()} {queue.data.total === 1 ? 'post' : 'posts'}
          {queue.data.comment_total != null && <> · {queue.data.comment_total.toLocaleString()} comments and replies</>}
        </p>
      )}
      {!queue.loading && queue.data?.total === 0 && <EmptyState icon={<MessagesSquare size={24} />} title="No matching posts" />}
      {!queue.loading && queue.data?.items.length > 0 && (
        <div className="stack">
          {queue.data.items.map((post) => (
            <div className="panel stack" key={post.id}>
              <p><strong>{post.facility || 'Unlinked facility'}</strong> · Facebook post #{post.id}</p>
              <p className="small muted">
                {post.page ? `Facebook · @${post.page}` : 'Facebook'} · {postStatus(post)}
                {post.comment_count != null && <> · {post.comment_count.toLocaleString()} comments and replies</>}
              </p>
              <button type="button" className="btn btn-secondary btn-sm" aria-expanded={selected === post.id}
                onClick={() => setSelected(selected === post.id ? null : post.id)}>
                {selected === post.id ? 'Close post' : 'Inspect post'}
              </button>
              {selected === post.id && <PostReview id={post.id} onSaved={saved} />}
            </div>
          ))}
          <Pagination page={page} pages={queue.data.pages} total={queue.data.total} pageSize={queue.data.page_size} noun="posts"
            onChange={(value) => { setPage(value); setSelected(null); }} />
        </div>
      )}
    </>
  );
}
