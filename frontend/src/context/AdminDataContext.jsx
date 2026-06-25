import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api";

const AdminDataContext = createContext(null);

export function AdminDataProvider({ user, children }) {
  const [complaints, setComplaints] = useState([]);
  const [officers, setOfficers] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (user?.role !== "admin") {
      return;
    }

    setLoading(true);
    setError("");
    try {
      const [complaintsRes, officersRes, analyticsRes] = await Promise.all([
        apiRequest("/admin/complaints"),
        apiRequest("/admin/officers"),
        apiRequest("/admin/analytics")
      ]);
      setComplaints(complaintsRes.items || []);
      setOfficers(officersRes.items || []);
      setAnalytics(analyticsRes);
    } catch (err) {
      setError(err.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }, [user?.role]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh]);

  const counts = useMemo(
    () => ({
      total: analytics?.summary?.total_complaints ?? complaints.length,
      active: analytics?.summary?.active ?? 0,
      pending: analytics?.summary?.pending ?? 0,
      in_progress: analytics?.summary?.in_progress ?? 0,
      completed: analytics?.summary?.completed ?? 0,
      rejected: analytics?.summary?.rejected ?? 0,
      unassigned: analytics?.summary?.unassigned ?? 0,
      officers: analytics?.summary?.officers ?? officers.length
    }),
    [analytics, complaints.length, officers.length]
  );

  const value = useMemo(
    () => ({ complaints, officers, analytics, counts, loading, error, refresh }),
    [complaints, officers, analytics, counts, loading, error, refresh]
  );

  return <AdminDataContext.Provider value={value}>{children}</AdminDataContext.Provider>;
}

export function useAdminData() {
  const context = useContext(AdminDataContext);
  if (!context) {
    throw new Error("useAdminData must be used within AdminDataProvider");
  }
  return context;
}

export function useAdminDataOptional() {
  return useContext(AdminDataContext);
}
