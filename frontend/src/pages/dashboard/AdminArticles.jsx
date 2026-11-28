import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { api } from "../../services/api";
import { useFetch } from "../../hooks/useFetch";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { formatDate } from "../../data/labels";
import { DashboardHeader } from "../../components/DashboardParts";
import { Modal } from "../../components/Modal";
import { Checkbox, TextArea, TextInput } from "../../components/Forms";
import { Alert, ErrorState, LoadingState } from "../../components/Feedback";
import { useToast } from "../../components/Toast";

// The article body is written as plain text and saved in the same shape as the seeded articles:
// a line starting with "## " begins a section, a line starting with "- " is a list item and
// a blank line separates paragraphs.
export function sectionsToText(sections = []) {
  return sections
    .map((s) => {
      const parts = [`## ${s.heading}`, ...(s.paragraphs || [])];
      if (s.list?.length) parts.push(s.list.map((item) => `- ${item}`).join("\n"));
      return parts.join("\n\n");
    })
    .join("\n\n");
}

export function textToSections(text) {
  const sections = [];
  let current = null;
  let paragraph = [];
  const finishParagraph = () => {
    if (paragraph.length) current.paragraphs.push(paragraph.join(" "));
    paragraph = [];
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (line.startsWith("## ")) {
      if (current) finishParagraph();
      current = { heading: line.slice(3).trim(), paragraphs: [], list: [] };
      sections.push(current);
    } else if (!current) {
      if (line) return { error: "Start the body with a section heading line, for example: ## Overview" };
    } else if (!line) {
      finishParagraph();
    } else if (line.startsWith("- ")) {
      finishParagraph();
      current.list.push(line.slice(2).trim());
    } else {
      paragraph.push(line);
    }
  }
  if (current) finishParagraph();
  if (!sections.length) return { error: "Add at least one section, starting with a heading line such as: ## Overview" };
  const empty = sections.find((s) => !s.paragraphs.length && !s.list.length);
  if (empty) return { error: `The section "${empty.heading}" needs at least one paragraph or list item.` };
  return {
    sections: sections.map((s) => ({
      heading: s.heading,
      ...(s.paragraphs.length ? { paragraphs: s.paragraphs } : {}),
      ...(s.list.length ? { list: s.list } : {}),
    })),
  };
}

const lines = (text) =>
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

// one source per line: "Label | Publisher"
const referencesToText = (refs = []) =>
  refs.map((r) => (r.publisher ? `${r.label} | ${r.publisher}` : r.label)).join("\n");
const textToReferences = (text) =>
  lines(text).map((line) => {
    const [label, ...publisher] = line.split("|");
    return { label: label.trim(), publisher: publisher.join("|").trim() };
  });

const blank = {
  title: "",
  category: "",
  summary: "",
  read_minutes: 4,
  review_status: "Awaiting clinical review",
  related_services: [],
  body: "",
  questions: "",
  references: "",
};

const toForm = (a) => ({
  title: a.title,
  category: a.category,
  summary: a.summary,
  read_minutes: a.read_minutes,
  review_status: a.review_status,
  related_services: a.related_services || [],
  body: sectionsToText(a.sections),
  questions: (a.questions_to_ask || []).join("\n"),
  references: referencesToText(a.references),
});

const shownFields = ["title", "category", "summary", "read_minutes", "review_status"];

export default function AdminArticles() {
  useDocumentTitle("Health library articles");
  const toast = useToast();
  const result = useFetch(() => api.adminArticles(), []);
  const services = useFetch(() => api.services(), []);
  // editing: null (closed), { article: null } for a new article, or { article } being edited
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(blank);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const open = async (slug) => {
    setErrors({});
    setError(null);
    if (!slug) {
      setForm(blank);
      setEditing({ article: null });
      return;
    }
    try {
      const article = await api.adminArticle(slug);
      setForm(toForm(article));
      setEditing({ article });
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const toggleService = (slug) =>
    setForm({
      ...form,
      related_services: form.related_services.includes(slug)
        ? form.related_services.filter((s) => s !== slug)
        : [...form.related_services, slug],
    });

  const save = async (e) => {
    e.preventDefault();
    setErrors({});
    setError(null);
    const body = textToSections(form.body);
    if (body.error) {
      setErrors({ body: body.error });
      return;
    }
    const article = {
      title: form.title,
      category: form.category,
      summary: form.summary,
      read_minutes: Number(form.read_minutes),
      review_status: form.review_status,
      related_services: form.related_services,
      sections: body.sections,
      questions_to_ask: lines(form.questions),
      references: textToReferences(form.references),
    };
    try {
      const original = editing.article;
      if (original) {
        // send only what changed, so an unchanged article keeps its "updated" date
        const changes = Object.fromEntries(
          Object.entries(article).filter(
            ([key, value]) => JSON.stringify(value) !== JSON.stringify(original[key]),
          ),
        );
        if (Object.keys(changes).length === 0) {
          toast("No changes to save");
        } else {
          await api.updateArticle(original.slug, changes);
          toast("Article saved");
        }
      } else {
        await api.createArticle(article);
        toast("Draft saved. Publish it when it is ready for the public.");
      }
      setEditing(null);
      result.reload();
    } catch (err) {
      const fields = err.fields || {};
      setErrors(fields);
      const other = Object.entries(fields)
        .filter(([key]) => !shownFields.includes(key))
        .map(([, message]) => message);
      setError([err.message, ...other].join(" "));
    }
  };

  const setPublished = async (a, publish) => {
    try {
      await (publish ? api.publishArticle(a.slug) : api.unpublishArticle(a.slug));
      toast(publish ? "Article published" : "Article hidden from the public library");
      result.reload();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  return (
    <>
      <DashboardHeader
        title="Health library articles"
        description="Write and update articles. New articles stay hidden from the public library until you publish them."
        actions={
          <button className="btn btn-primary" onClick={() => open(null)}>
            <Plus size={16} aria-hidden="true" /> New article
          </button>
        }
      />
      {result.loading && <LoadingState rows={1} height={300} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Article</th>
                <th>Updated</th>
                <th>Status</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {result.data.map((a) => (
                <tr key={a.slug}>
                  <td>
                    {a.is_published ? (
                      <Link to={`/health-library/${a.slug}`}>
                        <strong>{a.title}</strong>
                      </Link>
                    ) : (
                      <strong>{a.title}</strong>
                    )}
                    <div className="small muted">
                      {a.category} · {a.review_status}
                    </div>
                  </td>
                  <td>{formatDate(a.updated_on)}</td>
                  <td>
                    <span className={`badge ${a.is_published ? "badge-success" : "badge-warning"}`}>
                      {a.is_published ? "Published" : "Draft"}
                    </span>
                  </td>
                  <td>
                    <div className="row" style={{ flexWrap: "nowrap" }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        aria-label={`Edit ${a.title}`}
                        onClick={() => open(a.slug)}
                      >
                        Edit
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        aria-label={`${a.is_published ? "Unpublish" : "Publish"} ${a.title}`}
                        onClick={() => setPublished(a, !a.is_published)}
                      >
                        {a.is_published ? "Unpublish" : "Publish"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <Modal
          title={editing.article ? "Edit article" : "New article"}
          description={
            editing.article
              ? editing.article.title
              : "Saved as a draft. Publish it from the list when it is ready."
          }
          onClose={() => setEditing(null)}
          width={760}
          footer={
            <>
              <button className="btn btn-secondary" onClick={() => setEditing(null)}>
                Cancel
              </button>
              <button className="btn btn-primary" form="article-form">
                {editing.article ? "Save changes" : "Save draft"}
              </button>
            </>
          }
        >
          <form id="article-form" className="form-grid" onSubmit={save} noValidate>
            {error && (
              <div className="span-2">
                <Alert tone="danger">{error}</Alert>
              </div>
            )}
            <TextInput
              className="span-2"
              label="Title"
              value={form.title}
              onChange={set("title")}
              error={errors.title}
              required
            />
            <TextInput
              label="Category"
              value={form.category}
              onChange={set("category")}
              error={errors.category}
              hint="For example: Family planning"
              required
            />
            <TextInput
              label="Reading time (minutes)"
              type="number"
              min={1}
              max={60}
              value={form.read_minutes}
              onChange={set("read_minutes")}
              error={errors.read_minutes}
            />
            <TextArea
              className="span-2"
              label="Summary"
              value={form.summary}
              onChange={set("summary")}
              error={errors.summary}
              required
            />
            <TextArea
              className="span-2"
              label="Article text"
              rows={14}
              value={form.body}
              onChange={set("body")}
              error={errors.body}
              hint='Start each section with "## " and its heading. Leave a blank line between paragraphs and start list items with "- ".'
              required
            />
            <TextArea
              label="Questions to ask a provider"
              value={form.questions}
              onChange={set("questions")}
              hint="One question per line."
            />
            <TextArea
              label="Sources"
              value={form.references}
              onChange={set("references")}
              hint='One per line: "Title | Publisher".'
            />
            <TextInput
              className="span-2"
              label="Review status"
              value={form.review_status}
              onChange={set("review_status")}
              error={errors.review_status}
              hint="Shown to readers, for example: Reviewed by a clinician, November 2026"
            />
            <fieldset className="span-2">
              <legend className="field-label">Related services</legend>
              <div className="row">
                {(services.data || []).map((s) => (
                  <Checkbox
                    key={s.slug}
                    label={s.name}
                    checked={form.related_services.includes(s.slug)}
                    onChange={() => toggleService(s.slug)}
                  />
                ))}
              </div>
            </fieldset>
          </form>
        </Modal>
      )}
    </>
  );
}
