import { Link } from "react-router-dom";
import { BookOpenText, ChevronDown } from "lucide-react";
import { scripted } from "../data/assistantContent";

export function AnswerSources({ sources }) {
  if (!sources?.length) return null;
  return (
    <ul className="bubble-sources">
      {sources.map((source) => (
        <li key={source.title}>
          <BookOpenText size={13} aria-hidden="true" />{" "}
          {source.articleId ? (
            <Link to={`/health-library/${source.articleId}`}>
              {source.title}
            </Link>
          ) : (
            source.title
          )}{" "}
          <span className="muted">({source.publisher})</span>
        </li>
      ))}
    </ul>
  );
}

export function HealthFaq({ lang }) {
  return scripted.map((topic) => (
    <details key={topic.id}>
      <summary>
        {topic.question[lang]} <ChevronDown size={18} aria-hidden="true" />
      </summary>
      <div className="assistant-faq-answer">
        {topic.paragraphs[lang].map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        {topic.bullets?.[lang] && (
          <ul>
            {topic.bullets[lang].map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
        {topic.uncertainty?.[lang] && (
          <p className="small muted">{topic.uncertainty[lang]}</p>
        )}
        <AnswerSources sources={topic.sources} />
      </div>
    </details>
  ));
}
