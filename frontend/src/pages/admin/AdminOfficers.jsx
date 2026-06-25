import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import OfficerCard from "../../components/admin/OfficerCard";
import { useAdminData } from "../../context/AdminDataContext";

export default function AdminOfficers({ user }) {
  const { officers, counts, loading, refresh, error } = useAdminData();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return officers;
    return officers.filter(
      (o) =>
        (o.name || "").toLowerCase().includes(query) ||
        (o.email || "").toLowerCase().includes(query) ||
        (o.department || "").toLowerCase().includes(query) ||
        (o.ward || "").toLowerCase().includes(query)
    );
  }, [officers, search]);

  if (user?.role !== "admin") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Admin access only</h2>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="rounded-3xl bg-white p-8 shadow-soft ring-1 ring-slate-100">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Officer management</p>
            <h2 className="mt-1 font-display text-3xl text-slate-900">Field officers</h2>
            <p className="mt-2 text-slate-500">
              {counts.officers} officers registered across departments and wards.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/dashboard/admin/register-officer" className="btn">
              + Register officer
            </Link>
            <button type="button" className="btn-secondary" onClick={refresh} disabled={loading}>
              {loading ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>
      </header>

      <div className="rounded-2xl bg-white p-4 shadow-soft ring-1 ring-slate-100">
        <div className="relative">
          <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
          <input
            type="search"
            className="input pl-10"
            placeholder="Search by name, email, department, or ward…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

      {loading && officers.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">Loading officers…</div>
      ) : filtered.length === 0 ? (
        <div className="rounded-3xl bg-white p-12 text-center shadow-soft">
          <p className="font-semibold text-slate-700">No officers found.</p>
          <Link to="/dashboard/admin/register-officer" className="btn mt-4 inline-block">
            Register first officer
          </Link>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((officer) => (
            <OfficerCard key={officer.officer_id} officer={officer} />
          ))}
        </div>
      )}
    </div>
  );
}
