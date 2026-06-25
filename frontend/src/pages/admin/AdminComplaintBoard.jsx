import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import AdminComplaintCard from "../../components/admin/AdminComplaintCard";
import { useAdminData } from "../../context/AdminDataContext";
import { filterComplaints, getStatusConfig } from "../../utils/officerUtils";

const PAGE_META = {
  all: {
    title: "All complaints",
    subtitle: "System-wide view of every complaint in the platform.",
    empty: "No complaints in the system yet.",
    status: "all"
  },
  active: {
    title: "Active complaints",
    subtitle: "Pending and in-progress cases requiring attention.",
    empty: "No active complaints.",
    status: "active"
  },
  PENDING: {
    title: "Pending",
    subtitle: "Awaiting officer acceptance or assignment.",
    empty: "No pending complaints.",
    status: "PENDING"
  },
  IN_PROGRESS: {
    title: "In progress",
    subtitle: "Officers are actively resolving these cases.",
    empty: "No in-progress complaints.",
    status: "IN_PROGRESS"
  },
  COMPLETED: {
    title: "Completed",
    subtitle: "Verified and closed complaints.",
    empty: "No completed complaints yet.",
    status: "COMPLETED"
  },
  REJECTED: {
    title: "Rejected",
    subtitle: "Submissions rejected by AI validation (no issue or private property).",
    empty: "No rejected submissions.",
    status: "REJECTED"
  }
};

function filterByPageStatus(items, pageStatus) {
  if (pageStatus === "all") return items;
  if (pageStatus === "active") {
    return items.filter((item) => {
      const s = item.status || "PENDING";
      return s === "PENDING" || s === "IN_PROGRESS";
    });
  }
  return filterComplaints(items, { status: pageStatus, search: "" });
}

export default function AdminComplaintBoard({ user, statusFilter = "all" }) {
  const meta = PAGE_META[statusFilter] || PAGE_META.all;
  const { complaints, counts, loading, refresh, error } = useAdminData();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("newest");

  const filteredItems = useMemo(() => {
    let result = filterByPageStatus(complaints, meta.status);
    result = filterComplaints(result, { status: "all", search });
    return [...result].sort((a, b) => {
      const dateA = new Date(a.created_at || 0).getTime();
      const dateB = new Date(b.created_at || 0).getTime();
      return sortBy === "newest" ? dateB - dateA : dateA - dateB;
    });
  }, [complaints, meta.status, search, sortBy]);

  if (user?.role !== "admin") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Admin access only</h2>
      </div>
    );
  }

  const headerStatus = statusFilter !== "all" && statusFilter !== "active" ? statusFilter : null;
  const config = headerStatus ? getStatusConfig(headerStatus) : null;

  return (
    <div className="space-y-6">
      <header className={`rounded-3xl p-8 shadow-soft ring-1 ring-slate-100 ${config?.header || "bg-white"}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            {config && (
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-2xl shadow-sm">
                {config.icon}
              </span>
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Complaint monitor</p>
              <h2 className="mt-1 font-display text-3xl text-slate-900">{meta.title}</h2>
              <p className="mt-2 text-slate-500">{meta.subtitle}</p>
            </div>
          </div>
          <button type="button" className="btn-secondary" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <Link
            to="/dashboard/admin/analytics"
            className="rounded-full px-3 py-1 text-xs font-semibold ring-1 bg-white text-slate-600 ring-slate-200 hover:bg-slate-50"
          >
            📊 Overview
          </Link>
          <Link
            to="/dashboard/admin/active"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "active"
                ? "bg-indigo-600 text-white ring-indigo-600"
                : "bg-white text-indigo-700 ring-indigo-200"
            }`}
          >
            Active ({counts.active})
          </Link>
          <Link
            to="/dashboard/admin/pending"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "PENDING"
                ? "bg-amber-600 text-white ring-amber-600"
                : "bg-white text-amber-700 ring-amber-200"
            }`}
          >
            Pending ({counts.pending})
          </Link>
          <Link
            to="/dashboard/admin/in-progress"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "IN_PROGRESS"
                ? "bg-blue-600 text-white ring-blue-600"
                : "bg-white text-blue-700 ring-blue-200"
            }`}
          >
            In progress ({counts.in_progress})
          </Link>
          <Link
            to="/dashboard/admin/completed"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "COMPLETED"
                ? "bg-emerald-600 text-white ring-emerald-600"
                : "bg-white text-emerald-700 ring-emerald-200"
            }`}
          >
            Completed ({counts.completed})
          </Link>
          <Link
            to="/dashboard/admin/rejected"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "REJECTED"
                ? "bg-red-600 text-white ring-red-600"
                : "bg-white text-red-700 ring-red-200"
            }`}
          >
            Rejected ({counts.rejected})
          </Link>
          <Link
            to="/dashboard/admin/all"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "all"
                ? "bg-slate-800 text-white ring-slate-800"
                : "bg-white text-slate-600 ring-slate-200"
            }`}
          >
            All ({counts.total})
          </Link>
        </div>
      </header>

      <div className="rounded-2xl bg-white p-4 shadow-soft ring-1 ring-slate-100">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
            <input
              type="search"
              className="input pl-10"
              placeholder="Search citizen, officer, ID, department, ward…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select className="input w-full sm:w-44" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

      {loading && complaints.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">Loading…</div>
      ) : filteredItems.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">
          <p className="font-semibold text-slate-700">{meta.empty}</p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {filteredItems.map((item) => (
            <AdminComplaintCard key={item.complaint_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
