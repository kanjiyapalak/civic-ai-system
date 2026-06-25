import React from "react";
import { Navigate } from "react-router-dom";

export default function DashboardHome({ user }) {
  if (user?.role === "admin") return <Navigate to="/dashboard/admin/analytics" replace />;
  if (user?.role === "officer") return <Navigate to="/dashboard/officer/analytics" replace />;
  if (user?.role === "citizen") return <Navigate to="/dashboard/citizen/analytics" replace />;

  return (
    <div className="rounded-3xl bg-white p-8 shadow-soft">
      <h2 className="font-display text-2xl">Welcome</h2>
    </div>
  );
}
