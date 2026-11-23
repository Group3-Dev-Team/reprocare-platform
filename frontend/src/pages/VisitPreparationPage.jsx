import { useRef, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ClipboardList,
  Download,
  Plus,
  Printer,
  Trash2,
  X,
} from "lucide-react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PageHeader } from "../components/PageHeader";
import { Checkbox, Select, TextInput } from "../components/Forms";
import { downloadFile } from "../services/downloadFile";
import "../styles/patient-tools.css";

const purposes = {
  general: {
    label: "General consultation",
    questions: [
      "What should I expect at this visit?",
      "What are my options and what might they cost?",
      "Who can I contact if I have questions after this visit?",
    ],
  },
  pregnancy: {
    label: "Pregnancy care",
    questions: [
      "What records or previous test results should I bring?",
      "What will we discuss at my first visit?",
      "How can I arrange follow-up care?",
    ],
  },
  contraception: {
    label: "Family planning",
    questions: [
      "Which options are available at this facility?",
      "What should I know about the benefits and possible side effects?",
      "What follow-up would each option involve?",
    ],
  },
  fertility: {
    label: "Fertility consultation",
    questions: [
      "What does the first consultation involve?",
      "Are there records you would like me to bring?",
      "Could I get an estimate of costs before deciding on next steps?",
    ],
  },
  screening: {
    label: "Screening or testing",
    questions: [
      "Do I need to prepare for the test?",
      "When and how will I get the results?",
      "Who should I talk to about my results?",
    ],
  },
};

const reminders = [
  "Confirm the address, hours and whether you need an appointment.",
  "Ask whether to bring identification, insurance details or previous results.",
  "Have an up-to-date list of any medicines or supplements for your clinician.",
  "Ask how to get results or arrange follow-up before you leave.",
];
const purposeOptions = Object.entries(purposes).map(([value, { label }]) => ({
  value,
  label,
}));
const intro =
  "Make a checklist of what to bring and the questions you want to ask.";

export default function VisitPreparationPage() {
  useDocumentTitle("Prepare for your visit", intro);
  const [params] = useSearchParams();
  const facility = params.get("facility");
  const facilityPath = /^[a-z0-9]+(?:-[a-z0-9]+)*$/i.test(facility || "")
    ? "/facilities/" + facility
    : null;
  const { state } = useLocation();
  const [purpose, setPurpose] = useState(() =>
    Object.hasOwn(purposes, state?.purpose) ? state.purpose : "general",
  );
  const [questions, setQuestions] = useState([]);
  const [customQuestion, setCustomQuestion] = useState("");
  const [checked, setChecked] = useState([]);
  const [status, setStatus] = useState("");
  const questionId = useRef(0);
  const selectedQuestions = questions.filter((question) =>
    question.text.trim(),
  );

  function addQuestion(text, suggestion) {
    if (!text.trim()) return;
    const id = ++questionId.current;
    setQuestions((current) => [
      ...current,
      { id, text: text.trim(), suggestion },
    ]);
    setStatus("Question added to your checklist.");
  }

  function removeQuestion(id) {
    setQuestions((current) => current.filter((question) => question.id !== id));
    setStatus("Question removed from your checklist.");
  }

  function clearChecklist() {
    setPurpose("general");
    setQuestions([]);
    setCustomQuestion("");
    setChecked([]);
    setStatus("Checklist cleared.");
  }

  function saveChecklist() {
    const lines = [
      "Prepare for your visit",
      "Visit purpose: " + purposes[purpose].label,
      "",
      "Questions for your healthcare professional",
      ...selectedQuestions.map((question) => "- " + question.text.trim()),
      "",
      "Before you go",
      ...reminders.map(
        (reminder) => (checked.includes(reminder) ? "[x] " : "[ ] ") + reminder,
      ),
      "",
    ];
    downloadFile(
      lines.join("\n"),
      "text/plain;charset=utf-8",
      "visit-checklist.txt",
    );
    setStatus("Checklist download started.");
  }

  return (
    <div className="visit-preparation">
      <PageHeader
        title="Prepare for your visit"
        intro={intro}
        crumbs={[{ label: "Prepare for your visit" }]}
      />
      <div className="container section-sm">
        <Link
          className="btn btn-ghost btn-sm visit-return"
          to={facilityPath || "/find-care/facilities"}
        >
          <ArrowLeft size={16} aria-hidden="true" />{" "}
          {facilityPath ? "Back to facility" : "Find care"}
        </Link>
        <div className="visit-tools-grid">
          <section
            className="panel stack"
            aria-labelledby="visit-questions-heading"
          >
            <h2 id="visit-questions-heading">Build your questions</h2>
            <Select
              label="Visit purpose"
              options={purposeOptions}
              value={purpose}
              onChange={(event) => setPurpose(event.target.value)}
            />
            <div className="visit-suggestions">
              <h3>Questions you can add</h3>
              {purposes[purpose].questions.map((suggestion) => {
                const selected = questions.find(
                  (question) => question.suggestion === suggestion,
                );
                return (
                  <button
                    className="btn btn-secondary btn-sm"
                    key={suggestion}
                    type="button"
                    aria-pressed={Boolean(selected)}
                    onClick={() =>
                      selected
                        ? removeQuestion(selected.id)
                        : addQuestion(suggestion, suggestion)
                    }
                  >
                    {selected ? (
                      <X size={16} aria-hidden="true" />
                    ) : (
                      <Plus size={16} aria-hidden="true" />
                    )}
                    {suggestion}
                  </button>
                );
              })}
            </div>
            <form
              className="visit-add-question"
              onSubmit={(event) => {
                event.preventDefault();
                addQuestion(customQuestion);
                setCustomQuestion("");
              }}
            >
              <TextInput
                label="Your own question"
                value={customQuestion}
                onChange={(event) => setCustomQuestion(event.target.value)}
                maxLength={280}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!customQuestion.trim()}
              >
                <Plus size={16} aria-hidden="true" /> Add question
              </button>
            </form>
            <div className="visit-question-list">
              <h3>Your question list</h3>
              {!questions.length && (
                <p className="small muted">
                  Add a suggestion or write your own question. You can edit any
                  question on your list.
                </p>
              )}
              {questions.length > 0 && (
                <ol>
                  {questions.map((question, index) => (
                    <li key={question.id}>
                      <TextInput
                        label={"Question " + (index + 1)}
                        value={question.text}
                        maxLength={280}
                        onChange={(event) => {
                          const text = event.target.value;
                          setQuestions((current) =>
                            current.map((item) =>
                              item.id === question.id
                                ? { ...item, text }
                                : item,
                            ),
                          );
                        }}
                      />
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        aria-label={"Remove question " + (index + 1)}
                        onClick={() => removeQuestion(question.id)}
                      >
                        <X size={18} aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </section>
          <aside className="visit-tools-aside stack">
            <section
              className="panel stack"
              aria-labelledby="visit-reminders-heading"
            >
              <h2 id="visit-reminders-heading">
                <ClipboardList size={21} aria-hidden="true" /> Before you go
              </h2>
              {reminders.map((reminder) => (
                <Checkbox
                  key={reminder}
                  label={reminder}
                  checked={checked.includes(reminder)}
                  onChange={(event) => {
                    const isChecked = event.target.checked;
                    setChecked((current) =>
                      isChecked
                        ? [...current, reminder]
                        : current.filter((item) => item !== reminder),
                    );
                  }}
                />
              ))}
              <a
                className="small"
                href="https://medlineplus.gov/ency/patientinstructions/000860.htm"
                target="_blank"
                rel="noreferrer"
              >
                MedlinePlus guide to preparing for a visit
              </a>
            </section>
            <section
              className="panel stack visit-save-panel"
              aria-labelledby="visit-save-heading"
            >
              <h2 id="visit-save-heading">Keep your checklist</h2>
              <p className="small muted">
                Your checklist is kept on this page until you leave. Download or
                print a copy to keep it, and avoid including private details on
                a shared device.
              </p>
              <div className="row">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={saveChecklist}
                >
                  <Download size={16} aria-hidden="true" /> Download checklist
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => window.print()}
                >
                  <Printer size={16} aria-hidden="true" /> Print
                </button>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm visit-clear"
                onClick={clearChecklist}
                disabled={
                  !(
                    purpose !== "general" ||
                    questions.length ||
                    checked.length ||
                    customQuestion
                  )
                }
              >
                <Trash2 size={16} aria-hidden="true" /> Clear checklist
              </button>
              <p className="sr-only" role="status">
                {status}
              </p>
            </section>
          </aside>
        </div>
      </div>
      <section className="visit-print" aria-hidden="true">
        <p className="visit-print-title">Prepare for your visit</p>
        <p>{purposes[purpose].label}</p>
        {selectedQuestions.length > 0 && (
          <>
            <h2>Your questions</h2>
            <ol>
              {selectedQuestions.map((question) => (
                <li key={question.id}>{question.text.trim()}</li>
              ))}
            </ol>
          </>
        )}
        <h2>Before you go</h2>
        <ul>
          {reminders.map((reminder) => (
            <li key={reminder}>
              {checked.includes(reminder) ? "[x] " : "[ ] "}
              {reminder}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
