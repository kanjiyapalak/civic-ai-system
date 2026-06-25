import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { AdminDataProvider, useAdminDataOptional } from "../context/AdminDataContext";
import { CitizenDataProvider, useCitizenDataOptional } from "../context/CitizenDataContext";
import { OfficerDataProvider, useOfficerDataOptional } from "../context/OfficerDataContext";

const adminNavSections = [
  {
    title: "Overview",
    items: [{ label: "Command Center", to: "/dashboard/admin/analytics", icon: "📊" }]
  },
  {
    title: "Complaints",
    items: [
      { label: "Active", to: "/dashboard/admin/active", icon: "🔔", countKey: "active", accent: "indigo" },
      { label: "Pending", to: "/dashboard/admin/pending", icon: "⏳", countKey: "pending", accent: "amber" },
      {
        label: "In Progress",
        to: "/dashboard/admin/in-progress",
        icon: "🔧",
        countKey: "in_progress",
        accent: "blue"
      },
      {
        label: "Completed",
        to: "/dashboard/admin/completed",
        icon: "✓",
        countKey: "completed",
        accent: "emerald"
      },
      { label: "Rejected", to: "/dashboard/admin/rejected", icon: "✕", countKey: "rejected", accent: "red" },
      { label: "All Complaints", to: "/dashboard/admin/all", icon: "📋", countKey: "total" }
    ]
  },
  {
    title: "Management",
    items: [
      { label: "Officers", to: "/dashboard/admin/officers", icon: "👮", countKey: "officers", accent: "indigo" },
      { label: "Register Officer", to: "/dashboard/admin/register-officer", icon: "＋" }
    ]
  }
];

const citizenNavSections = [
  {
    title: "Overview",
    items: [
      { label: "My Dashboard", to: "/dashboard/citizen/analytics", icon: "📊" },
      { label: "Report Issue", to: "/dashboard/make-complaint", icon: "＋" }
    ]
  },
  {
    title: "Track complaints",
    items: [
      { label: "Active", to: "/dashboard/citizen/active", icon: "🔔", countKey: "active", accent: "orange" },
      { label: "Pending", to: "/dashboard/citizen/pending", icon: "⏳", countKey: "pending", accent: "amber" },
      {
        label: "In Progress",
        to: "/dashboard/citizen/in-progress",
        icon: "🔧",
        countKey: "in_progress",
        accent: "blue"
      },
      {
        label: "Resolved",
        to: "/dashboard/citizen/completed",
        icon: "✓",
        countKey: "completed",
        accent: "emerald"
      },
      { label: "All Reports", to: "/dashboard/citizen/all", icon: "📋", countKey: "total" }
    ]
  }
];

const officerNavSections = [
  {
    title: "Overview",
    items: [{ label: "Analytics", to: "/dashboard/officer/analytics", icon: "📊" }]
  },
  {
    title: "Complaints",
    items: [
      { label: "Pending", to: "/dashboard/officer/pending", icon: "⏳", countKey: "pending", accent: "amber" },
      {
        label: "In Progress",
        to: "/dashboard/officer/in-progress",
        icon: "🔧",
        countKey: "in_progress",
        accent: "blue"
      },
      {
        label: "Completed",
        to: "/dashboard/officer/completed",
        icon: "✓",
        countKey: "completed",
        accent: "emerald"
      },
      { label: "All Complaints", to: "/dashboard/officer/all", icon: "📋", countKey: "total" }
    ]
  }
];

function NavBadge({ count, accent }) {
  if (!count) return null;
  const colors = {
    orange: "bg-orange-500",
    amber: "bg-amber-500",
    blue: "bg-blue-500",
    emerald: "bg-emerald-500",
    indigo: "bg-indigo-500",
    red: "bg-red-500"
  };
  return (
    <span
      className={`ml-auto flex h-5 min-w-[1.25rem] items-center justify-center rounded-full px-1.5 text-[10px] font-bold text-white ${
        colors[accent] || "bg-slate-500"
      }`}
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}

function RoleNav({ sections, useDataHook }) {
  const data = useDataHook();
  const counts = data?.counts || {};

  return (
    <>
      {sections.map((section) => (
        <div key={section.title} className="mt-6">
          <p className="mb-2 px-4 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">
            {section.title}
          </p>
          <div className="space-y-1">
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-600 hover:bg-indigo-50 hover:text-slate-900"
                  }`
                }
              >
                <span className="text-base opacity-80" aria-hidden="true">
                  {item.icon}
                </span>
                <span className="flex-1">{item.label}</span>
                {item.countKey && <NavBadge count={counts[item.countKey]} accent={item.accent} />}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

function DashboardShell({ user, onLogout }) {
  const isOfficer = user?.role === "officer";
  const isCitizen = user?.role === "citizen";
  const isAdmin = user?.role === "admin";

  const brandLabel = isAdmin ? "Admin Console" : isOfficer ? "Officer Desk" : isCitizen ? "Citizen Hub" : "Civic";
  const brandTitle = isAdmin ? "Command Center" : isOfficer ? "Workspace" : isCitizen ? "My Reports" : "Desk";

  return (
    <div className="min-h-screen bg-haze text-ink">
      <div className="flex min-h-screen">
        <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-6">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{brandLabel}</p>
            <h1 className="font-display text-2xl">{brandTitle}</h1>
          </div>

          <nav className="mt-8 flex-1 overflow-y-auto">
            {isCitizen && <RoleNav sections={citizenNavSections} useDataHook={useCitizenDataOptional} />}
            {isOfficer && <RoleNav sections={officerNavSections} useDataHook={useOfficerDataOptional} />}
            {isAdmin && <RoleNav sections={adminNavSections} useDataHook={useAdminDataOptional} />}
          </nav>

          <div className="mt-6 border-t border-slate-100 pt-6">
            <div className="rounded-2xl bg-slate-50 p-4 text-sm ring-1 ring-slate-100">
              <p className="font-semibold text-slate-800">{user?.name}</p>
              <p className="mt-0.5 capitalize text-slate-500">{user?.role}</p>
            </div>
            <button type="button" className="btn-secondary mt-4 w-full" onClick={onLogout}>
              Logout
            </button>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto px-6 py-8 lg:px-10 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout({ user, onLogout }) {
  if (user?.role === "admin") {
    return (
      <AdminDataProvider user={user}>
        <DashboardShell user={user} onLogout={onLogout} />
      </AdminDataProvider>
    );
  }

  if (user?.role === "officer") {
    return (
      <OfficerDataProvider user={user}>
        <DashboardShell user={user} onLogout={onLogout} />
      </OfficerDataProvider>
    );
  }

  if (user?.role === "citizen") {
    return (
      <CitizenDataProvider user={user}>
        <DashboardShell user={user} onLogout={onLogout} />
      </CitizenDataProvider>
    );
  }

  return <DashboardShell user={user} onLogout={onLogout} />;
}
