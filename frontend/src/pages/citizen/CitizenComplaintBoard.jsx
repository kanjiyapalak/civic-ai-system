import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import CitizenComplaintCard from "../../components/citizen/CitizenComplaintCard";
import { useCitizenData } from "../../context/CitizenDataContext";
import { filterComplaints, getStatusConfig } from "../../utils/officerUtils";

const PAGE_META = {
  all: {
    title: "All my complaints",
    subtitle: "Every report you've filed, searchable in one place.",
    empty: "You haven't filed any complaints yet.",
    status: "all"
  },
  active: {
    title: "Active requests",
    subtitle: "Complaints still being processed — pending or in progress.",
    empty: "No active complaints. All caught up!",
    status: "active"
  },
  PENDING: {
    title: "Pending",
    subtitle: "Submitted and waiting for an officer to pick up.",
    empty: "No pending complaints right now.",
    status: "PENDING"
  },
  IN_PROGRESS: {
    title: "In progress",
    subtitle: "An officer is working on these issues.",
    empty: "Nothing in progress at the moment.",
    status: "IN_PROGRESS"
  },
  COMPLETED: {
    title: "Resolved",
    subtitle: "Verified and closed complaints with resolution proof.",
    empty: "No resolved complaints yet — they'll appear here once verified.",
    status: "COMPLETED"
  }
};

function filterByPageStatus(items, pageStatus) {
  if (pageStatus === "all") {
    return items;
  }
  if (pageStatus === "active") {
    return items.filter((item) => {
      const status = item.status || "PENDING";
      return status === "PENDING" || status === "IN_PROGRESS";
    });
  }
  return filterComplaints(items, { status: pageStatus, search: "" });
}

export default function CitizenComplaintBoard({ user, statusFilter = "all" }) {
  const meta = PAGE_META[statusFilter] || PAGE_META.all;
  const { items, counts, loading, refresh, error } = useCitizenData();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("newest");

  const filteredItems = useMemo(() => {
    let result = filterByPageStatus(items, meta.status);
    result = filterComplaints(result, { status: "all", search });
    result = [...result].sort((a, b) => {
      const dateA = new Date(a.created_at || 0).getTime();
      const dateB = new Date(b.created_at || 0).getTime();
      return sortBy === "newest" ? dateB - dateA : dateA - dateB;
    });
    return result;
  }, [items, meta.status, search, sortBy]);

  if (user?.role !== "citizen") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Citizen access only</h2>
      </div>
    );
  }

  const headerStatus = statusFilter === "active" ? null : statusFilter !== "all" ? statusFilter : null;
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
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">My complaints</p>
              <h2 className="mt-1 font-display text-3xl text-slate-900">{meta.title}</h2>
              <p className="mt-2 text-slate-500">{meta.subtitle}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/dashboard/make-complaint" className="btn text-sm">
              + New report
            </Link>
            <button type="button" className="btn-secondary text-sm" onClick={refresh} disabled={loading}>
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <Link
            to="/dashboard/citizen/analytics"
            className="rounded-full px-3 py-1 text-xs font-semibold ring-1 bg-white text-slate-600 ring-slate-200 hover:bg-slate-50"
          >
            📊 Overview
          </Link>
          <Link
            to="/dashboard/citizen/active"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "active"
                ? "bg-orange-500 text-white ring-orange-500"
                : "bg-white text-orange-700 ring-orange-200 hover:bg-orange-50"
            }`}
          >
            Active ({counts.active})
          </Link>
          <Link
            to="/dashboard/citizen/pending"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "PENDING"
                ? "bg-amber-600 text-white ring-amber-600"
                : "bg-white text-amber-700 ring-amber-200 hover:bg-amber-50"
            }`}
          >
            Pending ({counts.pending})
          </Link>
          <Link
            to="/dashboard/citizen/in-progress"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "IN_PROGRESS"
                ? "bg-blue-600 text-white ring-blue-600"
                : "bg-white text-blue-700 ring-blue-200 hover:bg-blue-50"
            }`}
          >
            In progress ({counts.in_progress})
          </Link>
          <Link
            to="/dashboard/citizen/completed"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "COMPLETED"
                ? "bg-emerald-600 text-white ring-emerald-600"
                : "bg-white text-emerald-700 ring-emerald-200 hover:bg-emerald-50"
            }`}
          >
            Resolved ({counts.completed})
          </Link>
          <Link
            to="/dashboard/citizen/all"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "all"
                ? "bg-slate-800 text-white ring-slate-800"
                : "bg-white text-slate-600 ring-slate-200 hover:bg-slate-50"
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
              placeholder="Search by ID, description, issue, department, ward, or officer…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <select
            className="input w-full sm:w-44"
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>
        {search && (
          <p className="mt-3 text-sm text-slate-500">
            {filteredItems.length} result{filteredItems.length !== 1 ? "s" : ""} for &ldquo;{search}&rdquo;
          </p>
        )}
      </div>

      {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

      {loading && items.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">
          <p className="text-slate-500">Loading your complaints…</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">
          <p className="text-4xl">{config?.icon || "📋"}</p>
          <p className="mt-4 font-semibold text-slate-700">{meta.empty}</p>
          {search ? (
            <button type="button" className="btn-secondary mt-4" onClick={() => setSearch("")}>
              Clear search
            </button>
          ) : (
            <Link to="/dashboard/make-complaint" className="btn mt-4 inline-block">
              Report an issue
            </Link>
          )}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {filteredItems.map((item) => (
            <CitizenComplaintCard key={item.complaint_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
