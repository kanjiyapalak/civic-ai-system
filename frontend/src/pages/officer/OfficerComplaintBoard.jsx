import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import ComplaintCard from "../../components/officer/ComplaintCard";
import VerifyModal from "../../components/officer/VerifyModal";
import { useOfficerData } from "../../context/OfficerDataContext";
import { filterComplaints, getStatusConfig } from "../../utils/officerUtils";
import { apiRequest } from "../../api";

const PAGE_META = {
  all: {
    title: "All complaints",
    subtitle: "Search and manage every complaint assigned to you.",
    empty: "No complaints match your search.",
    status: "all"
  },
  PENDING: {
    title: "Pending complaints",
    subtitle: "New assignments waiting for your acceptance.",
    empty: "No pending complaints. You're all caught up!",
    status: "PENDING"
  },
  IN_PROGRESS: {
    title: "In progress",
    subtitle: "Active cases you're currently working on.",
    empty: "No complaints in progress right now.",
    status: "IN_PROGRESS"
  },
  COMPLETED: {
    title: "Completed",
    subtitle: "Verified and closed complaints with resolution proof.",
    empty: "No completed complaints yet.",
    status: "COMPLETED"
  }
};

export default function OfficerComplaintBoard({ user, statusFilter = "all" }) {
  const meta = PAGE_META[statusFilter] || PAGE_META.all;
  const { items, counts, loading, refresh, error } = useOfficerData();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [toast, setToast] = useState({ type: "", message: "" });
  const [activeComplaint, setActiveComplaint] = useState(null);
  const [updatingId, setUpdatingId] = useState(null);

  const filteredItems = useMemo(() => {
    let result = filterComplaints(items, { status: meta.status, search });
    result = [...result].sort((a, b) => {
      const dateA = new Date(a.created_at || 0).getTime();
      const dateB = new Date(b.created_at || 0).getTime();
      return sortBy === "newest" ? dateB - dateA : dateA - dateB;
    });
    return result;
  }, [items, meta.status, search, sortBy]);

  const handleMarkInProgress = async (complaintId) => {
    setUpdatingId(complaintId);
    try {
      await apiRequest(`/officer/complaints/${complaintId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: "IN_PROGRESS" })
      });
      await refresh();
      setToast({ type: "success", message: "Complaint accepted and marked in progress." });
    } catch (err) {
      setToast({ type: "error", message: err.message || "Failed to update status" });
    } finally {
      setUpdatingId(null);
    }
  };

  const handleVerifyComplete = async (result) => {
    await refresh();
    setActiveComplaint(null);
    if (result?.is_resolved) {
      setToast({ type: "success", message: "Verification passed — complaint marked completed." });
    } else {
      setToast({
        type: "error",
        message: "Verification failed — complaint remains in progress."
      });
    }
  };

  if (user?.role !== "officer") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Officer access only</h2>
      </div>
    );
  }

  const config = statusFilter !== "all" ? getStatusConfig(statusFilter) : null;

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
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Officer workspace</p>
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
            to="/dashboard/officer/pending"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "PENDING"
                ? "bg-amber-600 text-white ring-amber-600"
                : "bg-white text-amber-700 ring-amber-200 hover:bg-amber-50"
            }`}
          >
            Pending ({counts.pending})
          </Link>
          <Link
            to="/dashboard/officer/in-progress"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "IN_PROGRESS"
                ? "bg-blue-600 text-white ring-blue-600"
                : "bg-white text-blue-700 ring-blue-200 hover:bg-blue-50"
            }`}
          >
            In progress ({counts.in_progress})
          </Link>
          <Link
            to="/dashboard/officer/completed"
            className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
              statusFilter === "COMPLETED"
                ? "bg-emerald-600 text-white ring-emerald-600"
                : "bg-white text-emerald-700 ring-emerald-200 hover:bg-emerald-50"
            }`}
          >
            Completed ({counts.completed})
          </Link>
          <Link
            to="/dashboard/officer/all"
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
              placeholder="Search by ID, description, issue, department, or ward…"
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
            Showing {filteredItems.length} result{filteredItems.length !== 1 ? "s" : ""} for &ldquo;{search}&rdquo;
          </p>
        )}
      </div>

      {(error || toast.message) && (
        <div
          className={`rounded-xl px-4 py-3 text-sm ${
            error || toast.type === "error" ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-700"
          }`}
        >
          {error || toast.message}
        </div>
      )}

      {loading && items.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">
          <p className="text-slate-500">Loading complaints…</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">
          <p className="text-4xl">{config?.icon || "📋"}</p>
          <p className="mt-4 font-semibold text-slate-700">{meta.empty}</p>
          {search && (
            <button type="button" className="btn-secondary mt-4" onClick={() => setSearch("")}>
              Clear search
            </button>
          )}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {filteredItems.map((item) => (
            <ComplaintCard
              key={item.complaint_id}
              item={item}
              onMarkInProgress={handleMarkInProgress}
              onVerify={setActiveComplaint}
              updatingId={updatingId}
            />
          ))}
        </div>
      )}

      {activeComplaint && (
        <VerifyModal
          complaint={activeComplaint}
          onClose={() => setActiveComplaint(null)}
          onComplete={handleVerifyComplete}
        />
      )}
    </div>
  );
}
