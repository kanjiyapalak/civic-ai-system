import React from "react";
import { Link } from "react-router-dom";
import { useOfficerData } from "../../context/OfficerDataContext";

function StatCard({ label, value, sub, accent, to }) {
  const content = (
    <div
      className={`rounded-2xl p-6 shadow-soft ring-1 ring-slate-100 transition hover:shadow-md ${accent}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 font-display text-4xl font-bold text-slate-900">{value}</p>
      {sub && <p className="mt-2 text-sm text-slate-500">{sub}</p>}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="block">
        {content}
      </Link>
    );
  }
  return content;
}

function HorizontalBar({ label, count, max }) {
  const width = max > 0 ? Math.round((count / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500">{count}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-blue-500 transition-all"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

function WeeklyChart({ trend }) {
  const max = Math.max(...(trend || []).map((d) => d.count), 1);
  return (
    <div className="flex h-40 items-end justify-between gap-2">
      {(trend || []).map((day) => {
        const height = Math.max(8, Math.round((day.count / max) * 100));
        const label = new Date(day.date).toLocaleDateString(undefined, { weekday: "short" });
        return (
          <div key={day.date} className="flex flex-1 flex-col items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">{day.count}</span>
            <div
              className="w-full rounded-t-lg bg-gradient-to-t from-blue-600 to-blue-400"
              style={{ height: `${height}%`, minHeight: "8px" }}
              title={`${day.date}: ${day.count} complaints`}
            />
            <span className="text-[10px] text-slate-400">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function OfficerAnalytics({ user }) {
  const { analytics, counts, loading, refresh, error } = useOfficerData();

  if (user?.role !== "officer") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Officer access only</h2>
      </div>
    );
  }

  const summary = analytics?.summary || {};
  const maxIssue = Math.max(...(analytics?.by_issue_type || []).map((i) => i.count), 1);
  const maxDept = Math.max(...(analytics?.by_department || []).map((d) => d.count), 1);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Analytics</p>
          <h2 className="mt-2 font-display text-3xl text-slate-900">Performance overview</h2>
          <p className="mt-2 text-slate-500">
            Track workload, resolution speed, and verification success across your assigned ward.
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={refresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh data"}
        </button>
      </header>

      {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Active workload"
          value={summary.active_workload ?? counts.pending + counts.in_progress}
          sub={`${counts.pending} pending · ${counts.in_progress} in progress`}
          accent="bg-white"
          to="/dashboard/officer/pending"
        />
        <StatCard
          label="Pending"
          value={counts.pending}
          sub="Needs acceptance"
          accent="bg-amber-50/80"
          to="/dashboard/officer/pending"
        />
        <StatCard
          label="In progress"
          value={counts.in_progress}
          sub="Currently resolving"
          accent="bg-blue-50/80"
          to="/dashboard/officer/in-progress"
        />
        <StatCard
          label="Completed"
          value={counts.completed}
          sub={`${summary.resolution_rate ?? 0}% resolution rate`}
          accent="bg-emerald-50/80"
          to="/dashboard/officer/completed"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100 lg:col-span-1">
          <h3 className="font-display text-lg text-slate-900">Key metrics</h3>
          <dl className="mt-6 space-y-4">
            <div className="flex justify-between border-b border-slate-100 pb-3">
              <dt className="text-sm text-slate-500">Total assigned</dt>
              <dd className="font-semibold text-slate-800">{summary.total ?? 0}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-3">
              <dt className="text-sm text-slate-500">Avg. resolution time</dt>
              <dd className="font-semibold text-slate-800">
                {summary.avg_resolution_hours != null ? `${summary.avg_resolution_hours}h` : "—"}
              </dd>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-3">
              <dt className="text-sm text-slate-500">Verification success</dt>
              <dd className="font-semibold text-slate-800">
                {summary.verification_success_rate != null
                  ? `${summary.verification_success_rate}%`
                  : "—"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-slate-500">Verification attempts</dt>
              <dd className="font-semibold text-slate-800">{summary.verification_attempts ?? 0}</dd>
            </div>
          </dl>

          <div className="mt-8 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Quick actions</p>
            <Link to="/dashboard/officer/pending" className="btn-secondary block w-full text-center text-sm">
              Review pending ({counts.pending})
            </Link>
            <Link to="/dashboard/officer/in-progress" className="btn block w-full text-center text-sm">
              Continue in progress ({counts.in_progress})
            </Link>
          </div>
        </div>

        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100 lg:col-span-2">
          <h3 className="font-display text-lg text-slate-900">Complaints this week</h3>
          <p className="mt-1 text-sm text-slate-500">New assignments received per day</p>
          <div className="mt-6">
            <WeeklyChart trend={analytics?.weekly_trend} />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
          <h3 className="font-display text-lg text-slate-900">By issue type</h3>
          <div className="mt-6 space-y-4">
            {(analytics?.by_issue_type || []).length === 0 && (
              <p className="text-sm text-slate-500">No data yet.</p>
            )}
            {(analytics?.by_issue_type || []).map((entry) => (
              <HorizontalBar key={entry.name} label={entry.name} count={entry.count} max={maxIssue} />
            ))}
          </div>
        </div>

        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
          <h3 className="font-display text-lg text-slate-900">By department</h3>
          <div className="mt-6 space-y-4">
            {(analytics?.by_department || []).length === 0 && (
              <p className="text-sm text-slate-500">No data yet.</p>
            )}
            {(analytics?.by_department || []).map((entry) => (
              <HorizontalBar key={entry.name} label={entry.name} count={entry.count} max={maxDept} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
