import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../../api";
import { useAdminDataOptional } from "../../context/AdminDataContext";

export default function AdminRegisterOfficer({ user }) {
  const adminData = useAdminDataOptional();
  const [departments, setDepartments] = useState([]);
  const [countries, setCountries] = useState([]);
  const [states, setStates] = useState([]);
  const [cities, setCities] = useState([]);
  const [wards, setWards] = useState([]);

  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
    departmentId: "",
    country: "",
    state: "",
    city: "",
    wardId: ""
  });
  const [status, setStatus] = useState({ type: "", message: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.role !== "admin") return;
    const loadInitial = async () => {
      try {
        const depRes = await apiRequest("/admin/departments");
        setDepartments(depRes.items || []);
        const countryRes = await apiRequest("/admin/locations/countries");
        setCountries(countryRes.items || []);
      } catch (err) {
        setStatus({ type: "error", message: err.message || "Failed to load data" });
      }
    };
    loadInitial();
  }, [user]);

  useEffect(() => {
    if (!form.country) {
      setStates([]);
      return;
    }
    apiRequest(`/admin/locations/states?country=${encodeURIComponent(form.country)}`)
      .then((res) => setStates(res.items || []))
      .catch((err) => setStatus({ type: "error", message: err.message }));
  }, [form.country]);

  useEffect(() => {
    if (!form.country || !form.state) {
      setCities([]);
      return;
    }
    apiRequest(
      `/admin/locations/cities?country=${encodeURIComponent(form.country)}&state=${encodeURIComponent(form.state)}`
    )
      .then((res) => setCities(res.items || []))
      .catch((err) => setStatus({ type: "error", message: err.message }));
  }, [form.country, form.state]);

  useEffect(() => {
    if (!form.country || !form.state || !form.city) {
      setWards([]);
      return;
    }
    apiRequest(
      `/admin/locations/wards?country=${encodeURIComponent(form.country)}&state=${encodeURIComponent(form.state)}&city=${encodeURIComponent(form.city)}`
    )
      .then((res) => setWards(res.items || []))
      .catch((err) => setStatus({ type: "error", message: err.message }));
  }, [form.country, form.state, form.city]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    if (name === "country") {
      setForm((prev) => ({ ...prev, country: value, state: "", city: "", wardId: "" }));
      return;
    }
    if (name === "state") {
      setForm((prev) => ({ ...prev, state: value, city: "", wardId: "" }));
      return;
    }
    if (name === "city") {
      setForm((prev) => ({ ...prev, city: value, wardId: "" }));
      return;
    }
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus({ type: "", message: "" });
    setLoading(true);
    try {
      await apiRequest("/admin/create-officer", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          email: form.email,
          phone: form.phone,
          password: form.password,
          department_id: form.departmentId,
          ward_id: form.wardId
        })
      });
      setStatus({ type: "success", message: "Officer registered successfully." });
      setForm({
        name: "",
        email: "",
        phone: "",
        password: "",
        departmentId: "",
        country: "",
        state: "",
        city: "",
        wardId: ""
      });
      adminData?.refresh?.();
    } catch (err) {
      setStatus({ type: "error", message: err.message || "Failed to register officer" });
    } finally {
      setLoading(false);
    }
  };

  if (user?.role !== "admin") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Access restricted</h2>
        <p className="mt-2 text-slate-500">Only admins can register officers.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <header className="rounded-3xl bg-white p-8 shadow-soft ring-1 ring-slate-100">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Officer onboarding</p>
        <h2 className="mt-2 font-display text-3xl text-slate-900">Register a new officer</h2>
        <p className="mt-2 text-slate-500">
          Assign department and ward coverage.{" "}
          <Link to="/dashboard/admin/officers" className="font-semibold text-indigo-600 hover:underline">
            View all officers →
          </Link>
        </p>
      </header>

      <form className="rounded-3xl bg-white p-8 shadow-soft ring-1 ring-slate-100" onSubmit={handleSubmit}>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-slate-400">Officer details</h3>
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
              <input name="password" type="password" className="input mt-2" value={form.password} onChange={handleChange} required />
            </label>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-slate-400">Assignment</h3>
            <label className="text-sm font-semibold text-slate-700">
              Department
              <select name="departmentId" className="input mt-2" value={form.departmentId} onChange={handleChange} required>
                <option value="">Select department</option>
                {departments.map((dep) => (
                  <option key={dep.id} value={dep.id}>
                    {dep.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold text-slate-700">
              Country
              <select name="country" className="input mt-2" value={form.country} onChange={handleChange} required>
                <option value="">Select country</option>
                {countries.map((country) => (
                  <option key={country} value={country}>
                    {country}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold text-slate-700">
              State
              <select name="state" className="input mt-2" value={form.state} onChange={handleChange} disabled={!form.country} required>
                <option value="">Select state</option>
                {states.map((state) => (
                  <option key={state} value={state}>
                    {state}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold text-slate-700">
              City
              <select name="city" className="input mt-2" value={form.city} onChange={handleChange} disabled={!form.state} required>
                <option value="">Select city</option>
                {cities.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="mt-8">
          <label className="text-sm font-semibold text-slate-700">
            Ward
            <select name="wardId" className="input mt-2" value={form.wardId} onChange={handleChange} disabled={!form.city} required>
              <option value="">Select ward</option>
              {wards.map((ward) => (
                <option key={ward.id} value={ward.id}>
                  {ward.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        {status.message && (
          <div
            className={`mt-6 rounded-xl px-4 py-3 text-sm ${
              status.type === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
            }`}
          >
            {status.message}
          </div>
        )}

        <button className="btn mt-6" type="submit" disabled={loading}>
          {loading ? "Registering…" : "Register officer"}
        </button>
      </form>
    </div>
  );
}
