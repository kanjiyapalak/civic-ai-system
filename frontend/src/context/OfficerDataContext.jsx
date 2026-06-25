import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api";

const OfficerDataContext = createContext(null);

export function OfficerDataProvider({ user, children }) {
  const [items, setItems] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (user?.role !== "officer") {
      return;
    }

    setLoading(true);
    setError("");
    try {
      const [complaintsRes, analyticsRes] = await Promise.all([
        apiRequest("/officer/complaints"),
        apiRequest("/officer/analytics")
      ]);
      setItems(complaintsRes.items || []);
      setAnalytics(analyticsRes);
    } catch (err) {
      setError(err.message || "Failed to load officer data");
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
      total: analytics?.summary?.total ?? items.length,
      pending: analytics?.summary?.pending ?? 0,
      in_progress: analytics?.summary?.in_progress ?? 0,
      completed: analytics?.summary?.completed ?? 0
    }),
    [analytics, items.length]
  );

  const value = useMemo(
    () => ({
      items,
      analytics,
      counts,
      loading,
      error,
      refresh
    }),
    [items, analytics, counts, loading, error, refresh]
  );

  return <OfficerDataContext.Provider value={value}>{children}</OfficerDataContext.Provider>;
}

export function useOfficerData() {
  const context = useContext(OfficerDataContext);
  if (!context) {
    throw new Error("useOfficerData must be used within OfficerDataProvider");
  }
  return context;
}

export function useOfficerDataOptional() {
  return useContext(OfficerDataContext);
}
