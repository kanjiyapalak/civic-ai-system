import React, { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import DashboardLayout from "./pages/DashboardLayout.jsx";
import DashboardHome from "./pages/DashboardHome.jsx";
import MakeComplaint from "./pages/MakeComplaint.jsx";
import OfficerAnalytics from "./pages/officer/OfficerAnalytics.jsx";
import OfficerComplaintBoard from "./pages/officer/OfficerComplaintBoard.jsx";
import CitizenAnalytics from "./pages/citizen/CitizenAnalytics.jsx";
import CitizenComplaintBoard from "./pages/citizen/CitizenComplaintBoard.jsx";
import AdminAnalytics from "./pages/admin/AdminAnalytics.jsx";
import AdminComplaintBoard from "./pages/admin/AdminComplaintBoard.jsx";
import AdminOfficers from "./pages/admin/AdminOfficers.jsx";
import AdminRegisterOfficer from "./pages/admin/AdminRegisterOfficer.jsx";
import { clearToken, fetchCurrentUser, getToken } from "./auth";

function ProtectedRoute({ isReady, user, children }) {
  if (!isReady) return <div className="page">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function HomeRedirect({ user }) {
  if (user?.role === "admin") return <Navigate to="/dashboard/admin/analytics" replace />;
  if (user?.role === "officer") return <Navigate to="/dashboard/officer/analytics" replace />;
  if (user?.role === "citizen") return <Navigate to="/dashboard/citizen/analytics" replace />;
  return <DashboardHome user={user} />;
}

export default function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [isReady, setIsReady] = useState(false);

  const loadUser = async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setIsReady(true);
      return;
    }
    try {
      setUser(await fetchCurrentUser());
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setIsReady(true);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const handleLogin = (nextUser) => {
    setUser(nextUser);
    if (nextUser?.role === "admin") navigate("/dashboard/admin/analytics");
    else if (nextUser?.role === "officer") navigate("/dashboard/officer/analytics");
    else if (nextUser?.role === "citizen") navigate("/dashboard/citizen/analytics");
    else navigate("/dashboard");
  };

  return (
    <Routes>
      <Route path="/" element={user ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />} />
      <Route path="/login" element={<Login onLogin={handleLogin} />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute isReady={isReady} user={user}>
            <DashboardLayout user={user} onLogout={() => { clearToken(); setUser(null); navigate("/login"); }} />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomeRedirect user={user} />} />
        <Route path="make-complaint" element={<MakeComplaint user={user} />} />

        <Route path="admin/analytics" element={<AdminAnalytics user={user} />} />
        <Route path="admin/active" element={<AdminComplaintBoard user={user} statusFilter="active" />} />
        <Route path="admin/pending" element={<AdminComplaintBoard user={user} statusFilter="PENDING" />} />
        <Route path="admin/in-progress" element={<AdminComplaintBoard user={user} statusFilter="IN_PROGRESS" />} />
        <Route path="admin/completed" element={<AdminComplaintBoard user={user} statusFilter="COMPLETED" />} />
        <Route path="admin/rejected" element={<AdminComplaintBoard user={user} statusFilter="REJECTED" />} />
        <Route path="admin/all" element={<AdminComplaintBoard user={user} statusFilter="all" />} />
        <Route path="admin/officers" element={<AdminOfficers user={user} />} />
        <Route path="admin/register-officer" element={<AdminRegisterOfficer user={user} />} />

        <Route path="citizen/analytics" element={<CitizenAnalytics user={user} />} />
        <Route path="citizen/active" element={<CitizenComplaintBoard user={user} statusFilter="active" />} />
        <Route path="citizen/pending" element={<CitizenComplaintBoard user={user} statusFilter="PENDING" />} />
        <Route path="citizen/in-progress" element={<CitizenComplaintBoard user={user} statusFilter="IN_PROGRESS" />} />
        <Route path="citizen/completed" element={<CitizenComplaintBoard user={user} statusFilter="COMPLETED" />} />
        <Route path="citizen/all" element={<CitizenComplaintBoard user={user} statusFilter="all" />} />

        <Route path="officer/analytics" element={<OfficerAnalytics user={user} />} />
        <Route path="officer/pending" element={<OfficerComplaintBoard user={user} statusFilter="PENDING" />} />
        <Route path="officer/in-progress" element={<OfficerComplaintBoard user={user} statusFilter="IN_PROGRESS" />} />
        <Route path="officer/completed" element={<OfficerComplaintBoard user={user} statusFilter="COMPLETED" />} />
        <Route path="officer/all" element={<OfficerComplaintBoard user={user} statusFilter="all" />} />

        <Route path="register-officer" element={<Navigate to="/dashboard/admin/register-officer" replace />} />
        <Route path="complaint-status" element={<Navigate to="/dashboard/citizen/all" replace />} />
        <Route path="officer-complaints" element={<Navigate to="/dashboard/officer/all" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
