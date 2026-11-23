// Component tests for external public feedback. All data below is a labelled TEST FIXTURE.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ExternalComment, ExternalPostCard, GoogleRatingCard, PublicFeedbackSection, relativeTime } from '../components/PublicFeedback';
import AdminFacebookFeedback from '../pages/dashboard/AdminFacebookFeedback';
import { api } from '../services/api';

afterEach(() => vi.restoreAllMocks());

const comment = (over = {}) => ({
  id: 1,
  platform: 'facebook',
  platform_label: 'Facebook',
  author: 'Fixture P.',
  author_is_facility: false,
  text: 'Test fixture comment',
  published_at: null,
  published_at_approximate: false,
  collected_at: '2026-11-01T00:00:00Z',
  like_count: 3,
  source_rating: null,
  replies: [],
  ...over,
});

describe('relativeTime', () => {
  it('describes past dates in words', () => {
    const twoWeeks = new Date(Date.now() - 14 * 86400 * 1000).toISOString();
    expect(relativeTime(twoWeeks)).toBe('2 weeks ago');
    expect(relativeTime(null)).toBe('');
  });
});

describe('ExternalComment', () => {
  it('labels facility replies, likes and nests replies', () => {
    render(
      <ul>
        <ExternalComment comment={comment({ replies: [comment({ id: 2, author: 'Fixture Hospital', author_is_facility: true, text: 'Test fixture reply', like_count: 0 })] })} />
      </ul>,
    );
    expect(screen.getByText('Facility reply')).toBeInTheDocument();
    expect(screen.getByText(/3 likes on Facebook/)).toBeInTheDocument();
    expect(screen.getByText('Test fixture reply')).toBeInTheDocument();
  });

  it('attributes a Google star rating to Google', () => {
    render(
      <ul>
        <ExternalComment comment={comment({ platform: 'google', source_rating: 2, like_count: null })} />
      </ul>,
    );
    expect(screen.getByText(/2\/5 on Google/)).toBeInTheDocument();
    expect(screen.getByText(/not a ReproCare rating/)).toBeInTheDocument();
  });
});

describe('GoogleRatingCard', () => {
  it('always states that it is not a ReproCare rating', () => {
    render(<GoogleRatingCard google={{ rating: 4.1, rating_count: 1234, url: 'https://www.google.com/maps', attribution: 'Rating from Google Maps users. Not a ReproCare rating.', fetched_at: null }} />);
    expect(screen.getByText(/1,234 Google Maps ratings/)).toBeInTheDocument();
    expect(screen.getByText(/Not a ReproCare rating/)).toBeInTheDocument();
  });
});

describe('ExternalPostCard', () => {
  it('links to the original source and loads the full thread on demand', async () => {
    const spy = vi.spyOn(api, 'externalPostComments').mockResolvedValue({ items: [comment({ id: 9, text: 'Test fixture from page 1' })], total: 1, page: 1, pages: 1, page_size: 8 });
    render(
      <ExternalPostCard
        post={{ id: 5, platform: 'tiktok', platform_label: 'TikTok', url: 'https://www.tiktok.com/@fx/video/1', author: '@fx', caption: 'Test fixture caption', thumbnail_url: '', published_at: null, collected_at: '2026-11-01T00:00:00Z', comment_count: 6, preview: [comment({ platform: 'tiktok' })] }}
      />,
    );
    expect(screen.getByRole('link', { name: /Watch on TikTok/ })).toHaveAttribute('href', 'https://www.tiktok.com/@fx/video/1');
    fireEvent.click(screen.getByRole('button', { name: /Read all 6/ }));
    await waitFor(() => expect(screen.getByText('Test fixture from page 1')).toBeInTheDocument());
    expect(spy).toHaveBeenCalledWith(5, { page: 1, page_size: 8 }, { signal: expect.any(AbortSignal) });
  });

  it('labels shared-page feedback and paginates the expanded Facebook thread', async () => {
    const spy = vi.spyOn(api, 'externalPostComments').mockImplementation(async (_, { page }) => ({
      items: [comment({ text: `Fixture page ${page}` })], total: 9, pages: 2, page, page_size: 8,
    }));
    const url = 'https://www.facebook.com/fixture/posts/1';
    render(<ExternalPostCard post={{
      id: 8, platform: 'facebook', attribution_scope: 'organization', url, author: '', caption: '',
      comment_count: 9, preview: [],
    }} />);
    expect(screen.getByText(/Organization-level feedback/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Facebook/ })).toHaveAttribute('href', url);
    fireEvent.click(screen.getByRole('button', { name: /Read all 9/ }));
    await screen.findByText('Fixture page 1');
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await screen.findByText('Fixture page 2');
    expect(spy).toHaveBeenLastCalledWith(8, { page: 2, page_size: 8 }, { signal: expect.any(AbortSignal) });
  });

  it('loads collected posts through their own endpoint and displays replies with their parent', async () => {
    const approved = vi.spyOn(api, 'externalPostComments');
    const demo = vi.spyOn(api, 'facebookDemoComments');
    const collected = vi.spyOn(api, 'collectedFacebookComments').mockResolvedValue({
      items: [comment({
        text: 'Fixture collected parent',
        replies: [comment({ id: 2, author_is_facility: true, text: 'Fixture collected reply' })],
      })],
      total: 1, pages: 1, page: 1, page_size: 8,
    });
    render(<ExternalPostCard post={{
      id: 8, platform: 'facebook', attribution_scope: 'organization', display_status: 'collected',
      url: 'https://www.facebook.com/fixture/posts/1', page_url: 'https://www.facebook.com/fixture',
      page_name: 'Fixture page', caption: '', comment_count: 2, preview: [comment()],
    }} />);
    expect(screen.getByRole('link', { name: 'Fixture page' })).toHaveAttribute('href', 'https://www.facebook.com/fixture');
    fireEvent.click(screen.getByRole('button', { name: 'Read all 2' }));
    expect(await screen.findByText('Fixture collected reply')).toBeVisible();
    expect(screen.getByText('Fixture collected parent').closest('li')).toContainElement(screen.getByText('Fixture collected reply'));
    expect(screen.getByText('Organization reply')).toBeVisible();
    expect(collected).toHaveBeenCalledWith(8, { page: 1, page_size: 8 }, { signal: expect.any(AbortSignal) });
    expect(approved).not.toHaveBeenCalled();
    expect(demo).not.toHaveBeenCalled();
  });
});

it('opens withheld Facebook feedback and its hidden replies for inspection without moderating', async () => {
  const post = {
    id: 8, facility: 'Fixture Clinic', page: 'fixture', status: 'withheld', comment_count: 2,
    source_url: 'https://www.facebook.com/fixture/posts/1',
  };
  const facilities = [{ id: 73, name: 'Fixture Clinic' }];
  const list = vi.spyOn(api, 'adminFacebookPosts').mockImplementation(async ({ page }) => ({
    items: [post], total: 21, comment_total: 29, page, pages: 2, page_size: 20, facilities,
  }));
  vi.spyOn(api, 'adminFacebookPost').mockResolvedValue({
    ...post,
    profiles: [],
    comments: [
      comment({ id: 10, author: 'Fixture parent', text: 'Fixture stored parent', parent_id: null, status: 'held' }),
      comment({ id: 11, text: 'Fixture stored hidden reply', parent_id: 10, status: 'hidden' }),
    ],
  });
  const moderate = vi.spyOn(api, 'moderateFacebookPost');
  render(
    <MemoryRouter initialEntries={['/dashboard/admin/facebook-feedback']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AdminFacebookFeedback />
    </MemoryRouter>,
  );

  expect(screen.getByRole('tab', { name: 'All Posts', selected: true })).toBeInTheDocument();
  await screen.findByText('21 posts · 29 comments and replies');
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  await waitFor(() => expect(list).toHaveBeenLastCalledWith(
    { status: 'all', page: 2, facility_id: '', q: '' }, { signal: expect.any(AbortSignal) },
  ));
  fireEvent.change(await screen.findByRole('combobox', { name: 'Facility' }), { target: { value: '73' } });
  fireEvent.change(screen.getByRole('searchbox', { name: 'Search posts' }), { target: { value: ' fixture ' } });
  fireEvent.click(screen.getByRole('button', { name: 'Search' }));
  await waitFor(() => expect(list).toHaveBeenLastCalledWith(
    { status: 'all', page: 1, facility_id: '73', q: 'fixture' }, { signal: expect.any(AbortSignal) },
  ));

  expect(await screen.findByText(/Facebook · @fixture · Withheld · 2 comments and replies/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Inspect post' }));
  expect(await screen.findByRole('heading', { name: 'Stored comments and replies (2)' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Open original Facebook post' })).toHaveAttribute('href', post.source_url);
  expect(screen.getByText('Fixture stored parent')).toBeInTheDocument();
  expect(screen.getByText('Fixture stored hidden reply')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Fixture parent' })).toHaveAttribute('href', '#facebook-comment-10');
  expect(screen.queryByRole('button', { name: 'Publish selected feedback' })).not.toBeInTheDocument();
  expect(moderate).not.toHaveBeenCalled();
});

it('requires explicit attribution and comment selection before submitting a Facebook decision', async () => {
  const post = { id: 8, facility: 'Fixture Clinic', source_url: 'https://www.facebook.com/fixture/posts/1', reviewed_at: null };
  vi.spyOn(api, 'adminFacebookPosts').mockResolvedValue({ items: [post], total: 1, page: 1, pages: 1, page_size: 20 });
  vi.spyOn(api, 'adminFacebookPost').mockResolvedValue({
    ...post, profiles: [], comments: [{ ...comment(), status: 'held', parent_id: null }],
  });
  const save = vi.spyOn(api, 'moderateFacebookPost').mockResolvedValue({ published: true });
  render(
    <MemoryRouter initialEntries={['/dashboard/admin/facebook-feedback']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AdminFacebookFeedback />
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Inspect post' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Review for publication' }));
  const publish = screen.getByRole('button', { name: 'Publish selected feedback' });
  expect(publish).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Attribution'), { target: { value: 'facility' } });
  fireEvent.change(screen.getByLabelText('Internal decision note'), { target: { value: 'Fixture branch checked.' } });
  expect(publish).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(publish);
  await screen.findByText('Selected Facebook feedback was published.');
  expect(save).toHaveBeenCalledWith(8, {
    decision: 'publish', scope: 'facility', note: 'Fixture branch checked.', comment_ids: [1], reviewed_at: null,
  });
});


it('separates approved and collected Facebook activity by attribution and keeps written Google reviews opt-in', async () => {
  const org = { key: 'fixture', name: 'Fixture organization', total: 1, comment_total: 16, written_total: 16 };
  const publishedPost = {
    id: 8, platform: 'facebook', attribution_scope: 'facility', url: 'https://www.facebook.com/fixture/posts/8',
    caption: 'Fixture approved caption', comment_count: 2, preview: [comment({ text: 'Fixture approved comment' })],
  };
  const collectedPost = {
    ...publishedPost, id: 10, url: 'https://www.facebook.com/fixture/posts/10', display_status: 'collected',
    caption: 'Fixture collected caption', comment_count: 7, preview: [comment({ text: 'Fixture branch comment' })],
  };
  const sharedPost = {
    ...collectedPost, id: 9, attribution_scope: 'organization', url: 'https://www.facebook.com/fixture/posts/9',
    caption: '', comment_count: 16, preview: [comment({ text: 'Fixture organization comment' })],
  };
  const approvedOrgPost = {
    ...publishedPost, id: 11, attribution_scope: 'organization', url: 'https://www.facebook.com/fixture/posts/11',
    caption: 'Fixture approved organization caption', comment_count: 3,
  };
  const pagination = { total: 1, pages: 1, page: 1, page_size: 4 };
  vi.spyOn(api, 'facilityPublicPosts').mockImplementation(async (_, { page }) => ({
    total: 2, pages: 2, page, page_size: 1, items: [page === 1 ? publishedPost : approvedOrgPost],
  }));
  const demo = vi.spyOn(api, 'facebookDemoPosts');
  const collection = vi.spyOn(api, 'facilityCollectedFacebookPosts').mockImplementation(async (_, { scope }) => scope === 'facility'
    ? { ...pagination, items: [collectedPost], comment_total: 7, written_total: 8, related_organizations: [org] }
    : { ...pagination, items: [sharedPost], comment_total: 16, written_total: 16 });
  const written = { author: 'Fixture author', text: 'Fixture review', source: 'https://www.google.com/maps?cid=1' };
  const google = vi.spyOn(api, 'facilityGoogleReviews').mockResolvedValue({ reviews: [written, written], attributions: [] });
  const onWrittenCount = vi.fn();
  const summary = { data: { platforms: [], google: { rating: 4.9, rating_count: 30 } } };
  render(
    <MemoryRouter initialEntries={['/facilities/fixture#google-feedback']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PublicFeedbackSection slug="fixture" summary={summary} onWrittenCount={onWrittenCount} />
    </MemoryRouter>,
  );
  await waitFor(() => expect(onWrittenCount).toHaveBeenLastCalledWith({ facility: 11, organization: 20 }));
  const tile = within(screen.getByText('comments and replies').closest('.xsummary-tile'));
  expect(tile.getByText('28')).toBeVisible();
  expect(tile.getByText('9 branch · 19 organization-wide')).toBeVisible();
  expect(collection).toHaveBeenCalledWith('fixture', { scope: 'facility', page: 1 }, { signal: expect.any(AbortSignal) });
  expect(collection).toHaveBeenCalledWith('fixture', { scope: 'organization', organization: org.key, page: 1 }, { signal: expect.any(AbortSignal) });
  expect(screen.queryByRole('heading', { name: /organization-wide Facebook activity/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Facebook' }));
  expect(screen.getByRole('heading', { name: 'Approved Facebook feedback' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Collected Facebook feedback' })).toBeVisible();
  expect(screen.getByRole('heading', { name: /organization-wide Facebook activity/ })).toBeVisible();
  expect(await screen.findByText('Fixture organization comment')).toBeVisible();
  expect(demo).not.toHaveBeenCalled();
  expect(google).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Google' }));
  expect(google).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Load written Google Maps reviews' }));
  expect(await screen.findByText('Fixture review')).toBeInTheDocument();
  await waitFor(() => expect(onWrittenCount).toHaveBeenLastCalledWith({ facility: 12, organization: 20 }));
});

it('shows organization-only comment totals and keeps them stable across post pages', async () => {
  const empty = { items: [], total: 0, page: 1, pages: 1, page_size: 4, comment_total: 0, written_total: 0 };
  const organization = { key: 'fixture', name: 'Fixture organization', total: 2, comment_total: 6, written_total: 8 };
  vi.spyOn(api, 'facilityPublicPosts').mockResolvedValue(empty);
  vi.spyOn(api, 'facilityCollectedFacebookPosts').mockImplementation(async (_, { scope, page }) => scope === 'facility'
    ? { ...empty, related_organizations: [organization] }
    : { ...organization, page, pages: 2, page_size: 1, items: [{
      id: page, platform: 'facebook', attribution_scope: 'organization', display_status: 'collected',
      url: `https://www.facebook.com/fixture/posts/${page}`, caption: `Fixture post page ${page}`,
      comment_count: 3, preview: [comment({ id: page, text: `Fixture organization comment page ${page}` })],
    }] });
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PublicFeedbackSection slug="fixture" summary={{ data: { platforms: [] } }} />
    </MemoryRouter>,
  );
  expect(screen.getByText('Counting comments…')).toBeVisible();
  const tile = within((await screen.findByText('comments and replies')).closest('.xsummary-tile'));
  expect(tile.getByText('6')).toBeVisible();
  expect(tile.getByText('0 branch · 6 organization-wide')).toBeVisible();
  expect(await screen.findByText('Fixture organization comment page 1')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  expect(await screen.findByText('Fixture organization comment page 2')).toBeVisible();
  expect(tile.getByText('6')).toBeVisible();
});

it('keeps approved Facebook feedback visible when local collection display is unavailable', async () => {
  const post = {
    id: 8, platform: 'facebook', attribution_scope: 'facility', url: 'https://www.facebook.com/fixture/posts/8',
    caption: '', comment_count: 1, preview: [comment({ text: 'Fixture approved comment' })],
  };
  vi.spyOn(api, 'facilityPublicPosts').mockResolvedValue({ items: [post], total: 1, pages: 1, page: 1, page_size: 4 });
  vi.spyOn(api, 'facilityCollectedFacebookPosts').mockRejectedValue(Object.assign(new Error('Unavailable'), { status: 404 }));
  const demo = vi.spyOn(api, 'facebookDemoPosts');
  render(
    <MemoryRouter initialEntries={['/facilities/fixture']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PublicFeedbackSection slug="fixture" summary={{ data: { platforms: [] } }} />
    </MemoryRouter>,
  );
  expect(await screen.findByText('Fixture approved comment')).toBeVisible();
  const tile = within((await screen.findByText('comments and replies')).closest('.xsummary-tile'));
  expect(tile.getByText('1 branch · 0 organization-wide')).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Approved Facebook feedback' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Collected Facebook feedback' })).not.toBeInTheDocument();
  expect(demo).not.toHaveBeenCalled();
});
