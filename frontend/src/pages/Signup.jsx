import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest } from "../api";

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    password: ""
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    setIsSubmitting(true);

    try {
      await apiRequest("/auth/signup", {
        method: "POST",
        body: JSON.stringify(form)
      });
      setSuccess("Account created. You can login now.");
      setTimeout(() => navigate("/login"), 800);
    } catch (err) {
      setError(err.message || "Signup failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <form className="w-full max-w-md rounded-3xl bg-white p-8 shadow-soft" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <h1 className="font-display text-3xl">Create account</h1>
          <p className="text-slate-500">Citizen signup only</p>
        </div>
        {error && <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
        {success && <div className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}
        <div className="mt-6 space-y-4">
          <label className="text-sm font-semibold text-slate-700">
            Name
            <input name="name" className="input mt-2" value={form.name} onChange={handleChange} required />
          </label>
          <label className="text-sm font-semibold text-slate-700">
            Email
            <input name="email" type="email" className="input mt-2" value={form.email} onChange={handleChange} required />
          </label>
          <label className="text-sm font-semibold text-slate-700">
            Phone
            <input name="phone" className="input mt-2" value={form.phone} onChange={handleChange} required />
          </label>
          <label className="text-sm font-semibold text-slate-700">
            Password
            <input
              name="password"
              type="password"
              className="input mt-2"
              value={form.password}
              onChange={handleChange}
              required
            />
          </label>
        </div>
        <button className="btn mt-6 w-full" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating..." : "Sign up"}
        </button>
        <div className="mt-4 text-sm text-slate-500">
          Already have an account? <Link className="font-semibold text-blue-600" to="/login">Login</Link>
        </div>
      </form>
    </div>
  );
}
