import React from "react";
import { Link } from "react-router-dom";
import { formatDate, formatRelativeDate, getStatusConfig, resolveImageUrl } from "../../utils/officerUtils";

export default function AdminComplaintCard({ item }) {
  const config = getStatusConfig(item.status || "PENDING");

  return (
    <article className={`overflow-hidden rounded-2xl bg-white shadow-soft ring-1 ring-slate-100 ${config.card}`}>
      <div className={`flex items-center justify-between px-5 py-3 ${config.header}`}>
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.icon}</span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{config.label}</p>
            <p className="text-xs text-slate-500">{item.citizen || "Unknown citizen"}</p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${config.badge}`}>
          {(item.status || "PENDING").replace("_", " ")}
        </span>
      </div>

      <div className="p-5">
        <p className="line-clamp-2 text-sm font-semibold text-slate-800">{item.description || "No description"}</p>
        <p className="mt-2 font-mono text-xs text-slate-400">
          {item.complaint_id?.slice(0, 13)}… · {formatRelativeDate(item.created_at)}
        </p>

        {item.image_url && (
          <img
            src={resolveImageUrl(item.image_url)}
            alt="Complaint"
            className="mt-4 h-32 w-full rounded-xl object-cover"
          />
        )}

        <dl className="mt-4 grid gap-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Issue</dt>
            <dd className="text-right font-medium text-slate-700">{item.issue_type || "-"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Department</dt>
            <dd className="text-right font-medium text-slate-700">{item.department || "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Ward</dt>
            <dd className="text-right font-medium text-slate-700">{item.ward || "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Officer</dt>
            <dd className={`text-right font-medium ${item.officer ? "text-slate-700" : "text-amber-600"}`}>
              {item.officer || "Unassigned"}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">Updated</dt>
            <dd className="text-right font-medium text-slate-700">{formatDate(item.updated_at)}</dd>
          </div>
        </dl>

        {item.status === "REJECTED" && item.rejection_reason && (
          <div className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">{item.rejection_reason}</div>
        )}
      </div>
    </article>
  );
}
