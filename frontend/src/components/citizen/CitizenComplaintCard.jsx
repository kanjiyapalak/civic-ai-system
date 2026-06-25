import React, { useState } from "react";
import {
  CITIZEN_STATUS_HINTS,
  formatDate,
  formatRelativeDate,
  getStatusConfig,
  resolveImageUrl
} from "../../utils/officerUtils";

function StatusTimeline({ item }) {
  const status = item.status || "PENDING";
  const steps = [
    { key: "submitted", label: "Submitted", done: true, date: item.created_at },
    {
      key: "assigned",
      label: "Assigned",
      done: Boolean(item.department && item.officer),
      detail: item.officer ? `Officer: ${item.officer}` : null
    },
    {
      key: "progress",
      label: "In progress",
      done: status === "IN_PROGRESS" || status === "COMPLETED",
      date: status !== "PENDING" ? item.updated_at : null
    },
    {
      key: "completed",
      label: "Resolved",
      done: status === "COMPLETED",
      date: status === "COMPLETED" ? item.updated_at : null
    }
  ];

  return (
    <ol className="mt-4 space-y-0">
      {steps.map((step, index) => (
        <li key={step.key} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                step.done ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-500"
              }`}
            >
              {step.done ? "✓" : index + 1}
            </span>
            {index < steps.length - 1 && (
              <span className={`my-1 w-0.5 flex-1 min-h-[1.5rem] ${step.done ? "bg-emerald-300" : "bg-slate-200"}`} />
            )}
          </div>
          <div className="pb-4">
            <p className={`text-sm font-semibold ${step.done ? "text-slate-800" : "text-slate-400"}`}>
              {step.label}
            </p>
            {step.detail && <p className="text-xs text-slate-500">{step.detail}</p>}
            {step.date && step.done && (
              <p className="text-xs text-slate-400">{formatRelativeDate(step.date)}</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function CitizenComplaintCard({ item }) {
  const [expanded, setExpanded] = useState(false);
  const displayStatus =
    item.status === "REJECTED" ? "REJECTED" : item.is_duplicate ? "DUPLICATE" : item.status || "PENDING";
  const config = getStatusConfig(displayStatus);
  const hint = CITIZEN_STATUS_HINTS[displayStatus] || CITIZEN_STATUS_HINTS[item.status] || "";

  return (
    <article
      className={`overflow-hidden rounded-2xl bg-white shadow-soft ring-1 ring-slate-100 transition hover:shadow-md ${config.card}`}
    >
      <div className={`flex items-center justify-between px-5 py-3 ${config.header}`}>
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden="true">
            {config.icon}
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{config.label}</p>
            <p className="text-xs text-slate-500">{hint}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {item.is_duplicate && (
            <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
              Linked
            </span>
          )}
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${config.badge}`}>
            {(item.status || "PENDING").replace("_", " ")}
          </span>
        </div>
      </div>

      <div className="p-5">
        <p className="line-clamp-2 text-sm font-semibold text-slate-800">
          {item.description || "No description"}
        </p>
        <p className="mt-2 font-mono text-xs text-slate-400">
          ID: {item.complaint_id?.slice(0, 13)}… · {formatRelativeDate(item.created_at)}
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {item.image_url && (
            <figure>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Photo</p>
              <img
                src={resolveImageUrl(item.image_url)}
                alt="Complaint"
                className="h-28 w-full rounded-xl object-cover"
              />
            </figure>
          )}
          {item.status === "COMPLETED" && item.after_image_url && (
            <figure>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">After fix</p>
              <img
                src={resolveImageUrl(item.after_image_url)}
                alt="After resolution"
                className="h-28 w-full rounded-xl object-cover"
              />
            </figure>
          )}
        </div>

        <dl className="mt-4 grid gap-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Issue</dt>
            <dd className="text-right font-medium text-slate-700">{item.issue_type || "-"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Department</dt>
            <dd className="text-right font-medium text-slate-700">{item.department || "Assigning…"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Ward</dt>
            <dd className="text-right font-medium text-slate-700">{item.ward || "Assigning…"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Officer</dt>
            <dd className="text-right font-medium text-slate-700">{item.officer || "Assigning…"}</dd>
          </div>
        </dl>

        <button
          type="button"
          className="mt-4 flex w-full items-center justify-between rounded-xl bg-slate-50 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100"
          onClick={() => setExpanded(!expanded)}
        >
          Track progress
          <span className="text-xs text-slate-400">{expanded ? "Hide" : "View timeline"}</span>
        </button>

        {expanded && <StatusTimeline item={item} />}

        {item.is_duplicate && item.parent && (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <p className="font-semibold text-slate-700">Linked to existing complaint</p>
            <p className="mt-1 text-xs text-slate-500">
              Your report was merged with a nearby case. Progress follows the parent complaint.
            </p>
            <dl className="mt-3 space-y-1.5">
              <div className="flex justify-between">
                <dt className="text-slate-400">Parent ID</dt>
                <dd className="font-mono text-xs text-slate-600">{item.parent.complaint_id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-400">Status</dt>
                <dd className="font-medium text-slate-700">{item.parent.status}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-400">Officer</dt>
                <dd className="font-medium text-slate-700">{item.parent.officer || "-"}</dd>
              </div>
            </dl>
          </div>
        )}

        {item.status === "REJECTED" && item.rejection_reason && (
          <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">
            <p className="font-semibold">Why this was not accepted</p>
            <p className="mt-1 text-xs">{item.rejection_reason}</p>
            {item.issue_confidence != null && (
              <p className="mt-1 text-xs text-red-600">AI confidence: {Math.round(item.issue_confidence)}%</p>
            )}
          </div>
        )}

        {item.status === "COMPLETED" && (
          <div className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <p className="font-semibold">Verified resolution</p>
            <p className="mt-1 text-xs">
              Location match: {item.location_match ? "Yes" : "No"} · Issue resolved:{" "}
              {item.issue_solved ? "Yes" : "No"} · Closed {formatDate(item.updated_at)}
            </p>
          </div>
        )}
      </div>
    </article>
  );
}
