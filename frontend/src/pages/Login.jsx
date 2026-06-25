import React, { useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../api";
import { fetchCurrentUser, setToken } from "../auth";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const result = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      setToken(result.access_token);
      const currentUser = await fetchCurrentUser();
      onLogin(currentUser);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <form className="w-full max-w-md rounded-3xl bg-white p-8 shadow-soft" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <h1 className="font-display text-3xl">Welcome back</h1>
          <p className="text-slate-500">Login to manage complaints</p>
        </div>
        {error && <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
        <div className="mt-6 space-y-4">
          <label className="text-sm font-semibold text-slate-700">
            Email
            <input
              className="input mt-2"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="text-sm font-semibold text-slate-700">
            Password
            <input
              className="input mt-2"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
        </div>
        <button className="btn mt-6 w-full" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Login"}
        </button>
        <div className="mt-4 text-sm text-slate-500">
          New here? <Link className="font-semibold text-blue-600" to="/signup">Create an account</Link>
        </div>
      </form>
    </div>
  );
}
