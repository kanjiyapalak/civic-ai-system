import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api";

const CitizenDataContext = createContext(null);

export function CitizenDataProvider({ user, children }) {
  const [items, setItems] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (user?.role !== "citizen") {
      return;
    }

    setLoading(true);
    setError("");
    try {
      const [complaintsRes, analyticsRes] = await Promise.all([
        apiRequest("/citizen/complaints"),
        apiRequest("/citizen/analytics")
      ]);
      setItems(complaintsRes.items || []);
      setAnalytics(analyticsRes);
    } catch (err) {
      setError(err.message || "Failed to load your complaints");
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
      completed: analytics?.summary?.completed ?? 0,
      active: analytics?.summary?.active ?? 0,
      duplicates: analytics?.summary?.duplicates ?? 0
    }),
    [analytics, items.length]
  );

  const value = useMemo(
    () => ({ items, analytics, counts, loading, error, refresh }),
    [items, analytics, counts, loading, error, refresh]
  );

  return <CitizenDataContext.Provider value={value}>{children}</CitizenDataContext.Provider>;
}

export function useCitizenData() {
  const context = useContext(CitizenDataContext);
  if (!context) {
    throw new Error("useCitizenData must be used within CitizenDataProvider");
  }
  return context;
}

export function useCitizenDataOptional() {
  return useContext(CitizenDataContext);
}
