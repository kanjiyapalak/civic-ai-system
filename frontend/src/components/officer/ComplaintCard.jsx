import React from "react";
import {
  formatDate,
  formatRelativeDate,
  getStatusConfig,
  resolveImageUrl
} from "../../utils/officerUtils";

export default function ComplaintCard({
  item,
  onMarkInProgress,
  onVerify,
  updatingId
}) {
  const config = getStatusConfig(item.status || "PENDING");
  const isPending = item.status === "PENDING";
  const isCompleted = item.status === "COMPLETED";

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
            <p className="text-xs text-slate-500">{config.description}</p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${config.badge}`}>
          {config.label}
        </span>
      </div>

      <div className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="line-clamp-2 flex-1 text-sm font-semibold text-slate-800">
            {item.description || "No description"}
          </p>
          <span className="shrink-0 text-xs text-slate-400">{formatRelativeDate(item.created_at)}</span>
        </div>

        <p className="mt-2 font-mono text-xs text-slate-400">#{item.complaint_id?.slice(0, 8)}…</p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {item.image_url && (
            <figure>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Before</p>
              <img
                src={resolveImageUrl(item.image_url)}
                alt="Before"
                className="h-28 w-full rounded-xl object-cover"
              />
            </figure>
          )}
          {isCompleted && item.after_image_url && (
            <figure>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">After</p>
              <img
                src={resolveImageUrl(item.after_image_url)}
                alt="After"
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
            <dd className="text-right font-medium text-slate-700">{item.department || "-"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Ward</dt>
            <dd className="text-right font-medium text-slate-700">{item.ward || "-"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Created</dt>
            <dd className="text-right font-medium text-slate-700">{formatDate(item.created_at)}</dd>
          </div>
          {isCompleted && (
            <>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-400">Location match</dt>
                <dd className={`font-medium ${item.location_match ? "text-emerald-600" : "text-red-500"}`}>
                  {item.location_match ? "Yes" : "No"}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-400">Issue resolved</dt>
                <dd className={`font-medium ${item.issue_solved ? "text-emerald-600" : "text-red-500"}`}>
                  {item.issue_solved ? "Yes" : "No"}
                </dd>
              </div>
            </>
          )}
        </dl>

        {!isCompleted && (
          <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
            {isPending && (
              <button
                type="button"
                className="btn-secondary text-xs"
                onClick={() => onMarkInProgress(item.complaint_id)}
                disabled={updatingId === item.complaint_id}
              >
                {updatingId === item.complaint_id ? "Updating…" : "Accept & Start"}
              </button>
            )}
            <button type="button" className="btn text-xs" onClick={() => onVerify(item)}>
              {item.status === "IN_PROGRESS" ? "Submit Resolution" : "Mark Completed"}
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
