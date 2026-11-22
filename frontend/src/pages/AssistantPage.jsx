import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertOctagon,
  ArrowRight,
  ArrowUp,
  RotateCcw,
  Search,
  ShieldCheck,
} from "lucide-react";
import {
  personalTerms,
  scripted,
  ui,
  urgentTerms,
} from "../data/assistantContent";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { AnswerSources, HealthFaq } from "../components/HealthFaq";
import { PageHeader } from "../components/PageHeader";
import "../styles/resource-pages.css";

// Short terms match whole words only, so "anc" does not match "cancer".
const has = (text, term) =>
  term.length <= 4
    ? new RegExp(`(^|[^a-z])${term}`, "i").test(text)
    : text.includes(term);

/** Choose a reviewed answer. Emergencies and personal medical questions are recognised first. */
export function respond(text) {
  const t = text.toLowerCase();
  if (urgentTerms.some((u) => t.includes(u))) return { kind: "urgent" };
  if (personalTerms.some((u) => t.includes(u))) return { kind: "personal" };
  const hit = scripted.find((s) => s.match.some((m) => has(t, m)));
  return hit ? { kind: "answer", id: hit.id } : { kind: "unknown" };
}

const topics = {
  en: [
    "Pregnancy care",
    "Fertility",
    "Family planning",
    "STI testing",
    "Cervical screening",
    "Community programmes",
  ],
  sw: [
    "Huduma za ujauzito",
    "Ushauri wa uzazi",
    "Uzazi wa mpango",
    "Vipimo vya magonjwa ya zinaa",
    "Uchunguzi wa shingo ya kizazi",
    "Kampeni za jamii",
  ],
};
const navigationQuestions = {
  en: [
    "Where can I find a laboratory?",
    "Where can I look for care by insurance?",
  ],
  sw: [
    "Ninaweza kupata maabara wapi?",
    "Ninaweza kupata huduma kwa bima wapi?",
  ],
};

export default function AssistantPage() {
  useDocumentTitle(
    "Health assistant",
    "General reproductive health information in English or Kiswahili.",
  );
  const [lang, setLang] = useState("en");
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const chatLog = useRef(null);
  const input = useRef(null);
  const L = ui[lang];

  useEffect(() => {
    if (messages.length && chatLog.current)
      chatLog.current.scrollTop = chatLog.current.scrollHeight;
  }, [messages]);

  const ask = (question) => {
    const q = question.trim();
    if (!q) return;
    setMessages((current) => [
      ...current,
      { role: "user", text: q, lang },
      { role: "bot", lang, ...respond(q) },
    ]);
    setText("");
  };

  return (
    <div className="resource-page resource-assistant">
      <PageHeader
        title="Health assistant"
        intro="Explore general questions about reproductive health in English or Kiswahili."
        crumbs={[
          { label: "Health & community", to: "/health-community/programmes" },
          { label: "Health assistant" },
        ]}
        tone="green"
      />
      <div className="container resource-main assistant-layout">
        <div className="assistant-main">
          <section
            className="chat panel"
            lang={lang}
            aria-label={
              lang === "sw" ? "Maswali na majibu" : "Questions and answers"
            }
          >
            <div className="chat-head">
              <div>
                <h2>{L.title}</h2>
                <p className="small muted">
                  {lang === "sw"
                    ? "Chagua mada au andika swali."
                    : "Choose a topic or type a question."}
                </p>
              </div>
              <div
                className="segmented"
                role="group"
                aria-label={lang === "sw" ? "Lugha" : "Language"}
              >
                <button
                  type="button"
                  aria-pressed={lang === "en"}
                  onClick={() => setLang("en")}
                  lang="en"
                >
                  English
                </button>
                <button
                  type="button"
                  aria-pressed={lang === "sw"}
                  onClick={() => setLang("sw")}
                  lang="sw"
                >
                  Kiswahili
                </button>
              </div>
            </div>
            <div
              className="chat-log"
              role="log"
              aria-live="polite"
              aria-label={
                lang === "sw"
                  ? "Maswali na majibu yako"
                  : "Your questions and answers"
              }
              ref={chatLog}
            >
              {!messages.length && (
                <div className="chat-empty" lang={lang}>
                  <h3>{L.what}</h3>
                  <ul className="assistant-topic-list">
                    {scripted.map((topic, index) => (
                      <li key={topic.id}>
                        <button
                          type="button"
                          onClick={() => {
                            ask(topic.question[lang]);
                            input.current?.focus();
                          }}
                        >
                          <span>{topics[lang][index]}</span>
                          <ArrowRight size={16} aria-hidden="true" />
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {messages.map((message, i) => (
                <div key={i} lang={message.lang}>
                  {message.role === "user" ? (
                    <p className="bubble bubble-user">{message.text}</p>
                  ) : (
                    <BotMessage message={message} lang={message.lang} />
                  )}
                </div>
              ))}
            </div>
            <form
              className="chat-input"
              onSubmit={(event) => {
                event.preventDefault();
                ask(text);
              }}
            >
              <label className="sr-only" htmlFor="chat-q">
                {lang === "sw" ? "Swali lako" : "Your question"}
              </label>
              <input
                id="chat-q"
                ref={input}
                className="input"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder={L.placeholder}
                maxLength={300}
              />
              <button
                className="btn btn-primary"
                aria-label={lang === "sw" ? "Tuma swali" : "Send question"}
                disabled={!text.trim()}
              >
                <ArrowUp size={18} aria-hidden="true" />
              </button>
            </form>
            <div className="assistant-chat-footer" lang={lang}>
              <p className="small muted">{L.privacy}</p>
              {messages.length > 0 && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setMessages([]);
                    setText("");
                    input.current?.focus();
                  }}
                >
                  <RotateCcw size={15} aria-hidden="true" /> {L.newChat}
                </button>
              )}
            </div>
          </section>
          <section
            className="assistant-faq"
            lang={lang}
            aria-labelledby="assistant-faq"
          >
            <h2 id="assistant-faq">
              {lang === "sw"
                ? "Maswali yanayoulizwa mara kwa mara"
                : "Frequently asked questions"}
            </h2>
            <HealthFaq lang={lang} />
          </section>
        </div>
        <aside className="assistant-aside" lang={lang}>
          <section className="resource-help">
            <ShieldCheck size={24} aria-hidden="true" />
            <h2>{lang === "sw" ? "Kuhusu msaidizi" : "About the assistant"}</h2>
            <p>{L.mode}</p>
            <ul className="small">
              <li>{L.b1}</li>
              <li>{L.b2}</li>
              <li>{L.b3}</li>
            </ul>
          </section>
          <section className="resource-help">
            <h2>
              {lang === "sw" ? "Jaribu kuuliza" : "More questions to try"}
            </h2>
            <ul className="assistant-starters">
              {navigationQuestions[lang].map((question) => (
                <li key={question}>
                  <button
                    type="button"
                    onClick={() => {
                      ask(question);
                      input.current?.focus();
                    }}
                  >
                    {question} <ArrowRight size={15} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </section>
          <section className="resource-help assistant-urgent">
            <AlertOctagon size={22} aria-hidden="true" />
            <h2>{lang === "sw" ? "Huduma za dharura" : "Emergency help"}</h2>
            <p className="small">
              {lang === "sw" ? "Kwa dharura, piga" : "In an emergency, call"}{" "}
              <a href="tel:999">999</a> / <a href="tel:112">112</a>.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}

function BotMessage({ message, lang }) {
  const L = ui[lang];
  if (message.kind === "urgent") {
    return (
      <div className="bubble bubble-urgent" role="alert">
        <strong>
          <AlertOctagon size={16} aria-hidden="true" /> {L.urgentT}
        </strong>
        <p>
          {L.urgentB} <a href="tel:999">999</a> / <a href="tel:112">112</a>
        </p>
        <p className="small">{L.urgentS}</p>
      </div>
    );
  }
  if (message.kind !== "answer") {
    return (
      <div className="bubble bubble-bot">
        <p>{message.kind === "personal" ? L.personal : L.unknown}</p>
        <Link to="/find-care/facilities" className="btn btn-secondary btn-sm">
          <Search size={14} aria-hidden="true" /> {L.find}
        </Link>
      </div>
    );
  }
  const a = scripted.find((s) => s.id === message.id);
  return (
    <div className="bubble bubble-bot">
      {a.paragraphs[lang].map((p) => (
        <p key={p}>{p}</p>
      ))}
      {a.bullets?.[lang] && (
        <ul>
          {a.bullets[lang].map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      )}
      {a.uncertainty?.[lang] && (
        <p className="small muted">{a.uncertainty[lang]}</p>
      )}
      <AnswerSources sources={a.sources} />
      <div className="row" style={{ marginTop: 8 }}>
        {a.serviceId && (
          <Link
            to={`/find-care/facilities?service=${a.serviceId}`}
            className="btn btn-secondary btn-sm"
          >
            <Search size={14} aria-hidden="true" /> {L.find} {L.near}
          </Link>
        )}
        {(a.nav || []).map((n) => (
          <Link key={n.href} to={n.href} className="btn btn-ghost btn-sm">
            {n.label[lang]}
          </Link>
        ))}
      </div>
    </div>
  );
}
