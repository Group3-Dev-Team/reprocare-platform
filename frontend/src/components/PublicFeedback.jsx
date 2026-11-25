/**
 * Public feedback collected from Facebook, TikTok and Google (SYSTEM 2).
 * Informational only: shown separately from ReproCare patient reviews and never used for ratings or ranking.
 */
import { useLocation } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Facebook, Heart, Info, Instagram, MapPin, MessagesSquare, Music2, Reply } from 'lucide-react';
import { api } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import { formatDate } from '../data/labels';
import { Pagination } from './Pagination';
import { EmptyState, ErrorState, LoadingState } from './Feedback';
import { Stars } from './Badges';

export const PLATFORMS = {
  facebook: { label: 'Facebook', icon: Facebook, verb: 'Post', open: 'View on Facebook' },
  tiktok: { label: 'TikTok', icon: Music2, verb: 'Video', open: 'Watch on TikTok' },
  google: { label: 'Google', icon: MapPin, verb: 'Listing', open: 'Open in Google Maps' },
  instagram: { label: 'Instagram', icon: Instagram },
};

export function relativeTime(iso) {
  if (!iso) return '';
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  if (!Number.isFinite(seconds)) return '';
  const steps = [
    [60, 'second'],
    [3600, 'minute'],
    [86400, 'hour'],
    [604800, 'day'],
    [2629800, 'week'],
    [31557600, 'month'],
    [Infinity, 'year'],
  ];
  const sizes = { second: 1, minute: 60, hour: 3600, day: 86400, week: 604800, month: 2629800, year: 31557600 };
  const [, unit] = steps.find(([limit]) => Math.abs(seconds) < limit);
  const n = Math.max(1, Math.round(seconds / sizes[unit]));
  return `${n} ${unit}${n === 1 ? '' : 's'} ago`;
}

export function PlatformPill({ platform, children }) {
  const p = PLATFORMS[platform];
  const Icon = p.icon;
  return (
    <span className={`platform-pill platform-${platform}`}>
      <Icon size={13} aria-hidden="true" />
      {children || p.label}
    </span>
  );
}

function initialsOf(name) {
  return (name || '?')
    .replace(/^@/, '')
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0] || '')
    .join('')
    .toUpperCase();
}

function TimeLabel({ comment }) {
  const iso = comment.published_at;
  if (!iso) return comment.collected_at ? <span title={`Collected ${formatDate(comment.collected_at)}`}>Collected {formatDate(comment.collected_at)}</span> : null;
  const full = formatDate(iso);
  return (
    <time dateTime={iso} title={comment.published_at_approximate ? `About ${full} (from the platform's “${relativeTime(iso)}” label)` : full}>
      {comment.published_at_approximate ? `about ${relativeTime(iso)}` : full}
    </time>
  );
}

export function ExternalComment({ comment, depth = 0, organization = false }) {
  return (
    <li className={`xc ${depth ? 'xc-reply' : ''} ${comment.author_is_facility ? 'xc-facility' : ''}`}>
      <span className={`xc-avatar platform-${comment.platform}`} aria-hidden="true">
        {initialsOf(comment.author)}
      </span>
      <div className="xc-main">
        <div className="xc-meta">
          <strong className="xc-author">{comment.author}</strong>
          {comment.author_is_facility && (
            <span className="xc-badge">
              <Reply size={11} aria-hidden="true" /> {organization ? 'Organization reply' : 'Facility reply'}
            </span>
          )}
          <span className="xc-dot" aria-hidden="true">·</span>
          <span className="xc-time">
            <TimeLabel comment={comment} />
          </span>
        </div>
        {comment.source_rating != null && (
          <p className="xc-rating">
            <Stars value={comment.source_rating} size={13} />
            <span>
              {comment.source_rating}/5 on Google <span className="sr-only">(a Google rating, not a ReproCare rating)</span>
            </span>
          </p>
        )}
        <p className="xc-text">{comment.text}</p>
        {comment.like_count > 0 && (
          <p className="xc-foot">
            <Heart size={12} aria-hidden="true" /> {comment.like_count.toLocaleString()} {comment.like_count === 1 ? 'like' : 'likes'} on {PLATFORMS[comment.platform].label}
          </p>
        )}
        {comment.replies?.length > 0 && (
          <ul className="xc-list">
            {comment.replies.map((r) => (
              <ExternalComment key={r.id} comment={r} depth={depth + 1} organization={organization} />
            ))}
          </ul>
        )}
      </div>
    </li>
  );
}

function CommentThread({ postId, organization, loadComments }) {
  const [page, setPage] = useState(1);
  const comments = useFetch((signal) => loadComments(postId, { page, page_size: 8 }, { signal }), [postId, page, loadComments]);
  return (
    <div className="xc-thread" aria-live="polite">
      {comments.loading && <LoadingState rows={2} height={64} label="Loading comments" />}
      {comments.error && <ErrorState error={comments.error} onRetry={comments.reload} />}
      {comments.data && (
        <>
          <ul className="xc-list">
            {comments.data.items.map((c) => (
              <ExternalComment key={c.id} comment={c} organization={organization} />
            ))}
          </ul>
          {comments.data.pages > 1 && (
            <Pagination page={comments.data.page} pages={comments.data.pages} total={comments.data.total} pageSize={comments.data.page_size} noun={comments.data.total === 1 ? 'comment' : 'top-level comments'} onChange={setPage} />
          )}
        </>
      )}
    </div>
  );
}

export function ExternalPostCard({ post, demo = false }) {
  const [expanded, setExpanded] = useState(false);
  const [captionOpen, setCaptionOpen] = useState(false);
  const p = PLATFORMS[post.platform];
  const collected = post.display_status === 'collected';
  const organization = post.attribution_scope === 'organization';
  const sourceScope = { organization: demo ? 'Organization activity · Branch unspecified' : 'Organization-level feedback · Branch unspecified', facility: demo ? 'Activity from this facility’s page' : 'Facility-specific Facebook feedback', unattributed: 'Collection only · Attribution unresolved' }[post.attribution_scope];
  const when = post.published_at || post.collected_at;
  const title =
    post.platform === 'google' ? 'Reviews on Google Maps' : post.author ? `${p.verb} by ${post.author}` : `${p.verb} on ${p.label}`;
  const longCaption = (post.caption || '').length > 220;

  return (
    <article className={`xpost xpost-${post.platform}`}>
      <header className="xpost-head">
        <PlatformPill platform={post.platform} />
        <div className="xpost-title">
          <h3>{title}</h3>
          {post.attribution_scope && (
            <p className="small muted">
              {sourceScope}
            </p>
          )}
          {(demo || collected) && post.page_url && <a className="small" href={post.page_url} target="_blank" rel="noopener noreferrer nofollow">{post.page_name}</a>}
          {when && (
            <p className="small muted">
              {post.published_at ? `${collected ? 'Posted on Facebook' : 'Published'} ${formatDate(post.published_at)}` : `Collected ${formatDate(post.collected_at)}`}
            </p>
          )}
        </div>
        <a className="btn btn-ghost btn-sm xpost-open" href={post.url} target="_blank" rel="noopener noreferrer nofollow">
          {p.open} <ExternalLink size={14} aria-hidden="true" />
        </a>
      </header>

      {(post.caption || post.thumbnail_url) && (
        <div className={`xpost-context ${post.thumbnail_url ? 'has-media' : ''}`}>
          {post.thumbnail_url && (
            <a href={post.url} target="_blank" rel="noopener noreferrer nofollow" className="xpost-media" aria-label={`${p.open} (opens in a new tab)`}>
              <img src={post.thumbnail_url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(e) => { e.currentTarget.closest('.xpost-media').style.display = 'none'; }} />
            </a>
          )}
          {post.caption && (
            <div>
              <p className={`xpost-caption ${longCaption && !captionOpen ? 'is-clamped' : ''}`}>{post.caption}</p>
              {longCaption && (
                <button type="button" className="link-btn small" onClick={() => setCaptionOpen((v) => !v)}>
                  {captionOpen ? 'Show less' : 'Read full post'}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {!expanded && post.preview.length > 0 && (
        <ul className="xc-list">
          {post.preview.map((c) => (
            <ExternalComment key={c.id} comment={c} organization={organization} />
          ))}
        </ul>
      )}
      {expanded && <CommentThread postId={post.id} organization={organization || post.attribution_scope === 'unattributed'}
        loadComments={collected ? api.collectedFacebookComments : demo ? api.facebookDemoComments : api.externalPostComments} />}

      <footer className="xpost-foot">
        <span className="small muted">
          <MessagesSquare size={14} aria-hidden="true" /> {post.comment_count} {post.platform === 'google' ? 'Google reviews' : 'public comments'} collected
        </span>
        {post.comment_count > post.preview.length && (
          <button type="button" className="btn btn-secondary btn-sm" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
            {expanded ? (
              <>
                Show fewer <ChevronUp size={15} aria-hidden="true" />
              </>
            ) : (
              <>
                Read all {post.comment_count} <ChevronDown size={15} aria-hidden="true" />
              </>
            )}
          </button>
        )}
      </footer>
    </article>
  );
}

/** Google's own rating, always attributed and visually distinct from the ReproCare rating. */
export function GoogleRatingCard({ google, compact = false }) {
  if (!google) return null;
  return (
    <div className={`google-rating ${compact ? 'is-compact' : ''}`}>
      <span className="google-rating-mark" aria-hidden="true">
        <MapPin size={compact ? 14 : 18} />
      </span>
      <div>
        <p className="google-rating-value">
          <strong>{google.rating.toFixed(1)}</strong>
          <Stars value={google.rating} size={compact ? 12 : 14} />
          <span className="muted">{google.rating_count == null ? 'Google Maps' : `${google.rating_count.toLocaleString()} Google Maps ratings`}</span>
        </p>
        {!compact && (
          <p className="small muted" style={{ margin: 0 }}>
            {google.attribution}
            {google.fetched_at && <> Checked {formatDate(google.fetched_at)}.</>}{' '}
            {google.url && (
              <a href={google.url} target="_blank" rel="noopener noreferrer">
                Open in Google Maps
              </a>
            )}
          </p>
        )}
      </div>
    </div>
  );
}

export function FeedbackItems({ result, onPage, demo = false }) {
  if (result.loading) return <LoadingState rows={2} height={100} label="Loading feedback" />;
  if (result.error) return <ErrorState error={result.error} onRetry={result.reload} />;
  if (!result.data?.total) return <EmptyState title="No activity available for this view" />;
  return (
    <div className="stack xpost-list">
      {result.data.items.map((post) => <ExternalPostCard key={post.id} post={post} demo={demo} />)}
      {result.data.pages > 1 && (
        <Pagination page={result.data.page} pages={result.data.pages} total={result.data.total}
          pageSize={result.data.page_size} noun="posts" onChange={onPage} />
      )}
    </div>
  );
}

function FacilityActivity({ slug, platform }) {
  const [page, setPage] = useState(1);
  const result = useFetch((signal) => api.facilityPublicPosts(slug, { platform, page, page_size: 4, preview: 3 }, { signal }),
    [slug, platform, page]);
  return <FeedbackItems result={result} onPage={setPage} />;
}

async function countFacebook(firstPage, loadPage, signal) {
  const posts = new Map();
  const addPage = ({ items }) => {
    for (const post of items) {
      if (!posts.has(post.id)) posts.set(post.id, post);
    }
  };
  addPage(firstPage);
  for (let page = 2; page <= firstPage.pages; page += 1) {
    addPage(await loadPage(page, signal));
  }
  // The API applies the same per-post visibility rules as the expanded thread.
  const counts = { facility: { comments: 0, written: 0 }, organization: { comments: 0, written: 0 } };
  for (const post of posts.values()) {
    if (post.attribution_scope === 'facility' || post.attribution_scope === 'organization') {
      const comments = Number(post.comment_count) || 0;
      const scope = counts[post.attribution_scope];
      scope.comments += comments;
      scope.written += comments + Number(!!post.caption?.trim());
    }
  }
  return counts;
}

// Shares each fetched page between the written-count pass and pagination, so a page is requested once.
// A cached request aborted by one consumer is retried for a consumer whose own signal is still live.
function usePageCache(loadPage) {
  return useMemo(() => {
    const cache = new Map();
    const fetchPage = (n, signal, retried = false) => {
      if (!cache.has(n)) {
        const request = loadPage(n, signal).catch((error) => {
          cache.delete(n);
          throw error;
        });
        cache.set(n, request);
      }
      return cache.get(n).catch((error) => {
        if (!retried && error?.name === 'AbortError' && signal && !signal.aborted) return fetchPage(n, signal, true);
        throw error;
      });
    };
    return fetchPage;
  }, [loadPage]);
}

function useFacebookPages(loadUncachedPage, page) {
  const loadPage = usePageCache(loadUncachedPage);
  const first = useFetch((signal) => loadPage(1, signal), [loadPage]);
  const later = useFetch((signal) => page > 1 ? loadPage(page, signal) : null, [loadPage, page]);
  return { result: page === 1 ? first : later, first, loadPage };
}

async function localFeedback(load) {
  if (!import.meta.env.DEV) return null;
  try {
    return await load();
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

function OrganizationActivity({ slug, organization }) {
  const [page, setPage] = useState(1);
  const loadPage = useCallback((n, signal) => localFeedback(() => api.facilityCollectedFacebookPosts(slug, {
    scope: 'organization', organization: organization.key, page: n,
  }, { signal })), [slug, organization.key]);
  const { result } = useFacebookPages(loadPage, page);
  const { total, comment_total: commentCount } = organization;
  return (
    <div className="stack">
      <h3>{organization.name} — organization-wide Facebook activity</h3>
      <p className="small muted">These posts come from the shared organization page. The comments cannot be attributed to this branch.</p>
      <p className="small muted">{total} {total === 1 ? 'post' : 'posts'} · {commentCount} {commentCount === 1 ? 'comment' : 'comments'} on the shared page</p>
      <FeedbackItems result={result} onPage={setPage} />
    </div>
  );
}

function distinctItems(items, keyFor) {
  return [...new Map(items.map((item) => [keyFor(item), item])).values()];
}

function GoogleWrittenReviews({ requested, onRequest, result, reviews }) {
  if (!requested) return <button type="button" className="btn btn-secondary btn-sm"
    onClick={onRequest}>Load written Google Maps reviews</button>;
  if (result.loading) return <LoadingState rows={2} height={90} label="Loading Google Maps reviews" />;
  if (result.error) {
    const message = {
      404: 'This facility does not have a linked Google Maps listing for written reviews.',
      503: 'Written Google Maps reviews are not available on this server. You can still see any ratings already shown here.',
      429: result.error.message,
    }[result.error.status] || 'Google Maps written reviews are temporarily unavailable. You can still see any ratings already shown here.';
    return <ErrorState error={{ message }} onRetry={result.reload} />;
  }
  if (!result.data) return null;
  if (!reviews.length) return <p className="small muted">{result.data.returned_count
    ? 'Google returned review entries without the text or attribution needed for display.'
    : 'Google Places returned no written reviews for this listing. Google Maps ratings can be left without a written review.'}</p>;
  return (
    <div className="stack">
      <p className="small muted">Google Maps supplies up to five reviews for this listing.</p>
      {reviews.map((review) => (
        <article className="xpost xpost-google" key={review.source}>
          <div className="row">
            {review.author_photo && <img src={review.author_photo} alt="" width="32" height="32" referrerPolicy="no-referrer" />}
            {review.author_url ? <a href={review.author_url} target="_blank" rel="noopener noreferrer">{review.author}</a> : <strong>{review.author}</strong>}
            <span className="small muted">Google Maps</span>
            {review.rating != null && <span>{review.rating}/5</span>}
            {review.published_at && <time dateTime={review.published_at}>{formatDate(review.published_at)}</time>}
          </div>
          <p>{review.text}</p>
          <a href={review.source} target="_blank" rel="noopener noreferrer">View this review on Google Maps</a>
        </article>
      ))}
      {result.data.attributions.map(({ provider, url }) => <p key={provider} className="small muted">
        {url ? <a href={url} target="_blank" rel="noopener noreferrer">{provider}</a> : provider}
      </p>)}
    </div>
  );
}

function InstagramActivity({ result, posts }) {
  if (result.loading) return <LoadingState rows={1} height={60} />;
  if (result.error) return <ErrorState error={result.error} onRetry={result.reload} />;
  if (!posts.length) return <EmptyState title="No authorized Instagram content is available for this facility" />;
  return (
    <div className="stack">
      <p className="small muted">Instagram public activity from an authorized capture.</p>
      {posts.map((post) => (
        <article className="xpost" key={post.url}>
          <h3>@{post.account}</h3>
          <p className="small muted">Collected {formatDate(post.captured_at)}</p>
          {post.caption && <p>{post.caption}</p>}
          <a href={post.url} target="_blank" rel="noopener noreferrer">View on Instagram</a>
          {post.comments.length > 0 && <ul>{post.comments.map((comment) =>
            <li key={JSON.stringify([comment.author, comment.text])}><strong>{comment.author}</strong> {comment.text}</li>
          )}</ul>}
        </article>
      ))}
    </div>
  );
}

const SOURCES = ['facebook', 'google', 'tiktok', 'instagram'];
const RUN_MESSAGES = {
  empty: 'checked, nothing public found',
  failed: 'could not be checked',
  skipped: 'not checked yet',
  succeeded: 'collected',
};

export function PublicFeedbackSection({ slug, summary, onWrittenCount }) {
  const { hash, key: locationKey } = useLocation();
  const [platform, setPlatform] = useState(hash === '#google-feedback' ? 'google' : '');
  const [publishedPage, setPublishedPage] = useState(1);
  const [collectedPage, setCollectedPage] = useState(1);
  const [googleRequested, setGoogleRequested] = useState(false);
  const [instagramRequested, setInstagramRequested] = useState(false);
  useEffect(() => {
    if (hash === '#google-feedback') setPlatform('google');
    if (hash === '#public-feedback') {
      setPlatform('');
      setPublishedPage(1);
      setCollectedPage(1);
    }
  }, [hash, locationKey]);

  const loadPublished = useCallback((page, signal) => api.facilityPublicPosts(
    slug, { platform: 'facebook', page, page_size: 4, preview: 3 }, { signal },
  ), [slug]);
  const { result: published, first: publishedFirst, loadPage: loadPublishedPage } = useFacebookPages(loadPublished, publishedPage);
  const publishedCount = useFetch(
    (signal) => publishedFirst.data ? countFacebook(publishedFirst.data, loadPublishedPage, signal) : null,
    [loadPublishedPage, publishedFirst.data],
  );

  const loadCollected = useCallback((page, signal) => localFeedback(() => api.facilityCollectedFacebookPosts(
    slug, { scope: 'facility', page }, { signal },
  )), [slug]);
  const { result: collected, first: collectedFirst } = useFacebookPages(loadCollected, collectedPage);

  const googleResult = useFetch((signal) => googleRequested ? api.facilityGoogleReviews(slug, { signal }) : null, [slug, googleRequested]);
  const googleReviews = useMemo(() => distinctItems(
    (googleResult.data?.reviews || []).filter((review) => review.text?.trim() && review.source && review.author),
    (review) => review.source,
  ), [googleResult.data]);
  const instagramResult = useFetch((signal) => instagramRequested
    ? localFeedback(() => api.instagramDemoPosts(slug, { signal })) : null, [slug, instagramRequested]);
  const instagramPosts = useMemo(() => distinctItems(instagramResult.data?.items || [], (post) => post.url).map((post) => ({
    ...post,
    comments: distinctItems(post.comments.filter((comment) => comment.text?.trim()), (comment) => JSON.stringify([comment.author, comment.text])),
  })), [instagramResult.data]);

  const s = summary.data;
  const google = s?.google;
  const sourceStats = Object.fromEntries(SOURCES.map((key) => [
    key, s?.platforms.find((entry) => entry.platform === key) || { posts: 0, comments: 0 },
  ]));
  const collectedData = collectedFirst.data;
  const organizations = collectedData?.related_organizations || [];
  const facebookBranchComments = (publishedCount.data?.facility.comments ?? 0) + (collectedData?.comment_total ?? 0);
  const facebookOrgComments = organizations.reduce((sum, org) => sum + org.comment_total, publishedCount.data?.organization.comments ?? 0);
  const facebookCountError = publishedFirst.error || publishedCount.error || collectedFirst.error;
  const facebookCountReady = !facebookCountError && !publishedFirst.loading && !collectedFirst.loading
    && (!publishedFirst.data?.total || !!publishedCount.data);
  const facebookComments = facebookCountReady ? facebookBranchComments + facebookOrgComments : null;
  const instagramCommentCount = instagramPosts.reduce((count, post) => count + post.comments.length, 0);
  const branch = (publishedCount.data?.facility.written ?? 0) + (collectedData?.written_total || 0) + sourceStats.tiktok.comments + googleReviews.length
    + instagramCommentCount + instagramPosts.filter((post) => post.caption?.trim()).length;
  const organizationCount = organizations.reduce((sum, org) => sum + org.written_total, publishedCount.data?.organization.written ?? 0);
  useEffect(() => {
    onWrittenCount?.({ facility: branch, organization: organizationCount });
  }, [branch, organizationCount, onWrittenCount]);

  const includes = (key) => platform === '' || platform === key;
  const hasCollected = !!(collectedData?.total || organizations.length);
  const hasFacebook = !!(publishedFirst.data?.total || hasCollected);
  const facebookSettled = !published.loading && !published.error && !collected.loading && !collected.error;
  const hasActivity = !!(hasFacebook || sourceStats.tiktok.posts || google || instagramPosts.length);
  const choose = (key) => {
    setPlatform(key);
    setPublishedPage(1);
    setCollectedPage(1);
    if (key === 'instagram') setInstagramRequested(true);
  };

  return (
    <section className="panel public-feedback" aria-labelledby="public-feedback-title" id="public-feedback">
      <div className="panel-title">
        <div>
          <h2 id="public-feedback-title">Public Reviews</h2>
          <p className="panel-sub">Browse public activity and ratings by source. Shared organisation pages are labelled separately.</p>
        </div>
        <span className="source source-external">
          <MessagesSquare size={13} aria-hidden="true" /> Collected public comments
        </span>
      </div>

      <div className="callout callout-neutral">
        <Info size={17} aria-hidden="true" />
        <p>
          {s?.notice || 'These public comments are for information only and do not affect any ReproCare rating or ranking.'}
          {' '}Names are shortened to protect privacy; each card links to the original source.
        </p>
      </div>

      {summary.loading && <LoadingState rows={1} height={74} />}
      {summary.error && <ErrorState error={summary.error} onRetry={summary.reload} />}

      <div className="xsummary">
        {SOURCES.map((key) => {
          const stats = sourceStats[key];
          const count = {
            google: google?.rating_count,
            facebook: facebookComments,
            tiktok: stats.comments,
            instagram: instagramCommentCount,
          }[key];
          const countLabel = {
            google: 'ratings',
            facebook: facebookCountError ? 'Count unavailable' : facebookCountReady ? 'comments and replies' : 'Counting comments…',
          }[key] || 'comments';
          const run = s?.last_runs?.[key];
          return (
            <div key={key} className={`xsummary-tile ${count ? '' : 'is-empty'}`}>
              <PlatformPill platform={key} />
              <strong>{count?.toLocaleString() ?? (key === 'facebook' || (key === 'google' && google) ? '—' : '0')}</strong>
              <span className="small muted">{countLabel}</span>
              {key === 'facebook' && facebookComments > 0 && (
                <span className="small muted">{facebookBranchComments.toLocaleString()} branch · {facebookOrgComments.toLocaleString()} organization-wide</span>
              )}
              {!count && (key !== 'facebook' || facebookCountReady) && run && (
                <span className="xsummary-run">{RUN_MESSAGES[run.status] || run.status} {run.at && `· ${formatDate(run.at)}`}</span>
              )}
            </div>
          );
        })}
      </div>
      <div className="chip-row" role="group" aria-label="Filter public reviews by source">
        {['', ...SOURCES].map((key) => (
          <button key={key || 'all'} type="button" aria-pressed={platform === key}
            className={`chip ${platform === key ? 'is-active' : ''}`} onClick={() => choose(key)}>
            {key ? PLATFORMS[key].label : 'All sources'}
          </button>
        ))}
      </div>

      <div id="google-feedback">
        {includes('google') && (google ? (
          <div className="stack">
            <GoogleRatingCard google={google} />
            {platform === 'google' && <GoogleWrittenReviews requested={googleRequested} onRequest={() => setGoogleRequested(true)} result={googleResult} reviews={googleReviews} />}
          </div>
        ) : platform === 'google' && !summary.loading && !summary.error && (s?.google_linked ? (
          <div className="stack">
            <p className="small muted">No Google Maps rating is stored for this facility yet. Written reviews come straight from its Google Maps listing.</p>
            <GoogleWrittenReviews requested={googleRequested} onRequest={() => setGoogleRequested(true)} result={googleResult} reviews={googleReviews} />
          </div>
        ) : (
          <EmptyState title="No Google rating available for this facility" />
        )))}
      </div>

      <div hidden={!includes('facebook')} className="stack">
        {!!publishedFirst.data?.total && <h3>Approved Facebook feedback</h3>}
        {(published.loading || published.error || !!publishedFirst.data?.total) && <FeedbackItems result={published} onPage={setPublishedPage} />}
        {hasCollected && (
          <div>
            <h3>Collected Facebook feedback</h3>
            <p className="small muted">These public Facebook posts and comments are unreviewed. They may include organization-wide activity.</p>
          </div>
        )}
        {(collected.loading || collected.error || !!collectedData?.total) && <FeedbackItems result={collected} onPage={setCollectedPage} />}
        {organizations.map((organization) => (
          <OrganizationActivity key={organization.key} slug={slug} organization={organization} />
        ))}
        {platform === 'facebook' && !hasFacebook && facebookSettled && <EmptyState title="No Facebook activity available for this facility" />}
      </div>

      {includes('tiktok') && (sourceStats.tiktok.posts > 0 || platform === 'tiktok') && (
        <FacilityActivity slug={slug} platform="tiktok" />
      )}
      {platform === 'instagram' && <InstagramActivity result={instagramResult} posts={instagramPosts} />}

      {platform === '' && !hasActivity && !summary.loading && !summary.error && facebookSettled && (
          <EmptyState icon={<MessagesSquare size={24} />} title="No public feedback available yet" />
      )}

      {s?.accounts?.length > 0 && (
        <p className="small muted xsources">
          Sources linked to this facility:{' '}
          {s.accounts.map((account, index) => (
            <span key={account.url}>
              {index > 0 && ' · '}
              <a href={account.url} target="_blank" rel="noopener noreferrer nofollow">
                {account.label}{account.name ? `: ${account.name}` : ''}
              </a>
            </span>
          ))}
        </p>
      )}
    </section>
  );
}
