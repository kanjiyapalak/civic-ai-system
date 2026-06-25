import React from "react";
import { Link } from "react-router-dom";
import { useAdminData } from "../../context/AdminDataContext";

function StatCard({ label, value, sub, accent, to }) {
  const inner = (
    <div className={`rounded-2xl p-6 shadow-soft ring-1 ring-slate-100 transition hover:shadow-md ${accent}`}>
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 font-display text-4xl font-bold text-slate-900">{value}</p>
      {sub && <p className="mt-2 text-sm text-slate-500">{sub}</p>}
    </div>
  );
  return to ? (
    <Link to={to} className="block">
      {inner}
    </Link>
  ) : (
    inner
  );
}

function HorizontalBar({ label, count, max, color = "bg-indigo-500" }) {
  const width = max > 0 ? Math.round((count / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500">{count}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${width}%` }} />
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
              className="w-full rounded-t-lg bg-gradient-to-t from-indigo-600 to-violet-400"
              style={{ height: `${height}%`, minHeight: "8px" }}
            />
            <span className="text-[10px] text-slate-400">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function AdminAnalytics({ user }) {
  const { analytics, counts, loading, refresh, error } = useAdminData();

  if (user?.role !== "admin") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Admin access only</h2>
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
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">System overview</p>
          <h2 className="mt-2 font-display text-3xl text-slate-900">Admin command center</h2>
          <p className="mt-2 text-slate-500">
            Monitor all complaints, officers, and city-wide resolution performance.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/dashboard/admin/register-officer" className="btn">
            Register officer
          </Link>
          <button type="button" className="btn-secondary" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Active complaints"
          value={summary.active ?? counts.active}
          sub={`${counts.pending} pending · ${counts.in_progress} in progress`}
          accent="bg-white"
          to="/dashboard/admin/active"
        />
        <StatCard
          label="Unassigned"
          value={summary.unassigned ?? counts.unassigned}
          sub="Need officer assignment"
          accent="bg-amber-50/80"
          to="/dashboard/admin/pending"
        />
        <StatCard
          label="Resolved"
          value={counts.completed}
          sub={`${summary.resolution_rate ?? 0}% resolution rate`}
          accent="bg-emerald-50/80"
          to="/dashboard/admin/completed"
        />
        <StatCard
          label="Rejected"
          value={counts.rejected}
          sub={`${summary.rejection_rate ?? 0}% rejection rate`}
          accent="bg-red-50/80"
          to="/dashboard/admin/rejected"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Citizens" value={summary.citizens ?? 0} accent="bg-slate-50" />
        <StatCard
          label="Officers"
          value={summary.officers ?? counts.officers}
          accent="bg-indigo-50/80"
          to="/dashboard/admin/officers"
        />
        <StatCard label="Departments" value={summary.departments ?? 0} accent="bg-slate-50" />
        <StatCard label="Wards" value={summary.wards ?? 0} accent="bg-slate-50" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100 lg:col-span-1">
          <h3 className="font-display text-lg text-slate-900">System metrics</h3>
          <dl className="mt-6 space-y-4">
            <div className="flex justify-between border-b border-slate-100 pb-3">
              <dt className="text-sm text-slate-500">Total complaints</dt>
              <dd className="font-semibold text-slate-800">{summary.total_complaints ?? 0}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-3">
              <dt className="text-sm text-slate-500">Avg. resolution time</dt>
              <dd className="font-semibold text-slate-800">
                {summary.avg_resolution_hours != null ? `${summary.avg_resolution_hours}h` : "—"}
              </dd>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-3">
              <dt className="text-sm text-slate-500">Resolution rate</dt>
              <dd className="font-semibold text-emerald-600">{summary.resolution_rate ?? 0}%</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-slate-500">Rejection rate</dt>
              <dd className="font-semibold text-red-600">{summary.rejection_rate ?? 0}%</dd>
            </div>
          </dl>
          <div className="mt-8 space-y-2">
            <Link to="/dashboard/admin/all" className="btn-secondary block w-full text-center text-sm">
              View all complaints
            </Link>
            <Link to="/dashboard/admin/officers" className="btn block w-full text-center text-sm">
              Manage officers ({counts.officers})
            </Link>
          </div>
        </div>

        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100 lg:col-span-2">
          <h3 className="font-display text-lg text-slate-900">Complaints this week</h3>
          <p className="mt-1 text-sm text-slate-500">New complaints filed per day</p>
          <div className="mt-6">
            <WeeklyChart trend={analytics?.weekly_trend} />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
          <h3 className="font-display text-lg text-slate-900">By issue type</h3>
          <div className="mt-6 space-y-4">
            {(analytics?.by_issue_type || []).map((entry) => (
              <HorizontalBar key={entry.name} label={entry.name} count={entry.count} max={maxIssue} />
            ))}
          </div>
        </div>
        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
          <h3 className="font-display text-lg text-slate-900">By department</h3>
          <div className="mt-6 space-y-4">
            {(analytics?.by_department || []).map((entry) => (
              <HorizontalBar
                key={entry.name}
                label={entry.name}
                count={entry.count}
                max={maxDept}
                color="bg-violet-500"
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
