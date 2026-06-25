import React from "react";
import { formatDate } from "../../utils/officerUtils";

export default function OfficerCard({ officer }) {
  return (
    <article className="rounded-2xl bg-white p-5 shadow-soft ring-1 ring-slate-100 transition hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-lg font-bold text-indigo-600">
          {(officer.name || "O").charAt(0).toUpperCase()}
        </div>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
          {officer.active_complaints ?? 0} active
        </span>
      </div>

      <h3 className="mt-4 font-semibold text-slate-900">{officer.name || "Unnamed officer"}</h3>
      <p className="text-sm text-slate-500">{officer.email}</p>

      <dl className="mt-4 space-y-2 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-400">Phone</dt>
          <dd className="font-medium text-slate-700">{officer.phone || "—"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-400">Department</dt>
          <dd className="text-right font-medium text-slate-700">{officer.department || "—"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-400">Ward</dt>
          <dd className="text-right font-medium text-slate-700">{officer.ward || "—"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-400">Registered</dt>
          <dd className="text-right font-medium text-slate-700">{formatDate(officer.created_at)}</dd>
        </div>
      </dl>
    </article>
  );
}
