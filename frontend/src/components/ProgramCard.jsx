import { Link } from "react-router-dom";
import { CalendarDays, Clock, MapPin, Users, Building2 } from "lucide-react";
import { costTypes, formatDate, programTypes } from "../data/labels";
import { DemoLabel } from "./Badges";

export function ProgramCard({ program }) {
  const date = new Date(`${program.start_date}T00:00:00`);
  const availability = program.is_past
    ? "Event ended"
    : program.spaces_left === 0
      ? "Full"
      : program.spaces_left > 0
        ? program.spaces_left + " places listed"
        : "Availability to confirm";
  return (
    <article className="program-card">
      <div className="program-date" aria-hidden="true">
        <span className="program-day">{date.getDate()}</span>
        <span className="program-month">
          {date.toLocaleDateString("en-KE", { month: "short" })}
        </span>
      </div>
      <div className="program-body">
        <div className="row" style={{ gap: 6 }}>
          <span
            className={`badge ${program.cost_type === "free" ? "badge-success" : "badge-info"}`}
          >
            {costTypes[program.cost_type]}
          </span>
          <span className="badge">{programTypes[program.program_type]}</span>
          {program.service && (
            <span className="badge badge-rose">{program.service.name}</span>
          )}
        </div>
        <h3>
          <Link to={`/programmes/${program.slug}`}>{program.title}</Link>
        </h3>
        <p className="small muted">{program.summary}</p>
        <ul className="program-facts">
          <li>
            <CalendarDays size={14} aria-hidden="true" />{" "}
            {formatDate(program.start_date, {
              weekday: "short",
              day: "numeric",
              month: "short",
            })}
          </li>
          <li>
            <Clock size={14} aria-hidden="true" /> {program.start_time} –{" "}
            {program.end_time}
          </li>
          <li>
            <MapPin size={14} aria-hidden="true" /> {program.town}
          </li>
          <li>
            <Users size={14} aria-hidden="true" /> {availability}
          </li>
          {program.organizer_name && (
            <li>
              <Building2 size={14} aria-hidden="true" />{" "}
              {program.organizer_name}
            </li>
          )}
        </ul>
        {program.is_demo && <DemoLabel />}
      </div>
    </article>
  );
}
