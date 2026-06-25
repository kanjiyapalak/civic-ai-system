import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useCitizenDataOptional } from "../context/CitizenDataContext";
import { apiStreamRequest, consumeSSE } from "../utils/sse";

export default function MakeComplaint({ user }) {
  const citizenData = useCitizenDataOptional();
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState(null);
  const [location, setLocation] = useState({ lat: null, lon: null, status: "idle" });
  const [messages, setMessages] = useState([]);
  const [streamSteps, setStreamSteps] = useState([]);
  const [status, setStatus] = useState({ type: "", message: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const previewUrl = useMemo(() => {
    if (!photo) {
      return "";
    }
    return URL.createObjectURL(photo);
  }, [photo]);

  const canSubmit = description.trim() && photo && location.lat !== null && location.lon !== null;

  const handleLocation = () => {
    if (!navigator.geolocation) {
      setStatus({ type: "error", message: "Geolocation is not supported in this browser." });
      return;
    }
    setLocation((prev) => ({ ...prev, status: "loading" }));

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          status: "ready"
        });
      },
      () => {
        setLocation((prev) => ({ ...prev, status: "error" }));
        setStatus({ type: "error", message: "Unable to fetch location. Please allow access." });
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const buildBotSummary = (response) => {
    if (response?.status === "REJECTED") {
      return `Submission not accepted. ${
        response?.rejection_reason || "No civic issue was detected in your photo."
      }${response?.issue_confidence != null ? ` (AI confidence: ${Math.round(response.issue_confidence)}%)` : ""}. Please upload a clear photo that visibly shows the problem.`;
    }
    if (response?.is_duplicate) {
      return `Duplicate complaint recorded. Linked to ${response?.parent_complaint_id || "parent"}. Status: ${
        response?.parent_status || response?.status || "Pending"
      }. Ward: ${response?.parent_ward || response?.ward || "Pending"}. Department: ${
        response?.parent_department || response?.department || "Pending"
      }. Officer: ${response?.parent_officer || response?.officer || "Pending"}.`;
    }
    return `Complaint received. Ward: ${response?.ward || "Pending"}. Department: ${
      response?.department || "Pending"
    }. Assigned officer: ${response?.officer || "Pending"}.`;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus({ type: "", message: "" });

    if (!canSubmit) {
      setStatus({ type: "error", message: "Please add description, photo, and location." });
      return;
    }

    const submittedDescription = description.trim();
    setIsSubmitting(true);
    setStreamSteps([]);

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: submittedDescription
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const formData = new FormData();
      formData.append("description", submittedDescription);
      formData.append("latitude", String(location.lat));
      formData.append("longitude", String(location.lon));
      formData.append("image", photo);
      if (user?.user_id) {
        formData.append("user_id", user.user_id);
      }

      const response = await apiStreamRequest("/complaint/stream", {
        method: "POST",
        body: formData
      });

      let finalResponse = null;

      await consumeSSE(response, {
        step: (payload) => {
          setStreamSteps((prev) => [
            ...prev,
            {
              id: `${payload.step}-${prev.length}`,
              step: payload.step,
              message: payload.message,
              status: payload.status
            }
          ]);
        },
        error: (payload) => {
          throw new Error(payload.message || "Complaint processing failed");
        },
        complete: (payload) => {
          finalResponse = payload;
        }
      });

      const botMessage = {
        id: `bot-${Date.now()}`,
        role: "bot",
        content: buildBotSummary(finalResponse)
      };

      setMessages((prev) => [...prev, botMessage]);
      setDescription("");
      setPhoto(null);
      setStreamSteps([]);

      if (finalResponse?.status === "REJECTED") {
        setStatus({
          type: "error",
          message:
            finalResponse?.rejection_reason ||
            "No civic issue detected in your photo. Please submit a clearer image of the actual problem."
        });
      } else {
        setStatus({
          type: "success",
          message: `Complaint submitted. ID: ${finalResponse?.complaint_id}`
        });
      }
      citizenData?.refresh?.();
    } catch (err) {
      setStatus({ type: "error", message: err.message || "Failed to submit complaint" });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (user?.role !== "citizen") {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h2 className="font-display text-2xl">Citizen access only</h2>
        <p className="mt-2 text-slate-500">Only citizens can file new complaints.</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl space-y-6">
      <header className="rounded-3xl bg-white p-8 shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Make complaint</p>
        <h2 className="mt-2 font-display text-3xl">Report civic issues with a live snapshot</h2>
        <p className="mt-3 text-slate-500">
          Upload a photo, describe the issue, and share your live location. Watch each processing step live as the
          assistant routes your complaint.{" "}
          <Link to="/dashboard/citizen/all" className="font-semibold text-blue-600 hover:underline">
            View your reports →
          </Link>
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form className="rounded-3xl bg-white p-8 shadow-soft" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <label className="text-sm font-semibold text-slate-700">
              Description
              <textarea
                className="mt-2 min-h-[140px] w-full rounded-2xl border border-slate-200 p-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe the issue (e.g. pothole near the main road)."
                required
                disabled={isSubmitting}
              />
            </label>

            <label className="text-sm font-semibold text-slate-700">
              Photo
              <input
                type="file"
                accept="image/*"
                className="mt-2 block w-full text-sm text-slate-600"
                onChange={(event) => setPhoto(event.target.files?.[0] || null)}
                required
                disabled={isSubmitting}
              />
            </label>

            <div className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-600">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold">Live location</p>
                  <p className="text-xs text-slate-500">
                    {location.lat !== null
                      ? `Lat ${location.lat.toFixed(5)}, Lon ${location.lon.toFixed(5)}`
                      : "Location not captured"}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleLocation}
                  disabled={location.status === "loading" || isSubmitting}
                >
                  {location.status === "loading" ? "Fetching..." : "Use my location"}
                </button>
              </div>
            </div>
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

          <button className="btn mt-6" type="submit" disabled={isSubmitting || !canSubmit}>
            {isSubmitting ? "Processing..." : "Submit complaint"}
          </button>
        </form>

        <div className="rounded-3xl bg-white p-8 shadow-soft">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-xl">Assistant</h3>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                isSubmitting ? "bg-blue-100 text-blue-700" : "bg-blue-50 text-blue-600"
              }`}
            >
              {isSubmitting ? "Streaming" : "Live"}
            </span>
          </div>

          {streamSteps.length > 0 && (
            <div className="mt-6 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Processing steps</p>
              {streamSteps.map((step) => (
                <div key={step.id} className="rounded-xl bg-blue-50 px-3 py-2 text-sm text-blue-800">
                  {step.message}
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 space-y-4">
            {messages.length === 0 && streamSteps.length === 0 && (
              <div className="rounded-2xl bg-slate-100 p-4 text-sm text-slate-500">
                Share a complaint to start the conversation.
              </div>
            )}
            {messages.map((message) => (
              <div
                key={message.id}
                className={`rounded-2xl px-4 py-3 text-sm ${
                  message.role === "user" ? "ml-auto bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
                }`}
              >
                {message.content}
              </div>
            ))}
          </div>
          {previewUrl && (
            <div className="mt-6">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Preview</p>
              <img src={previewUrl} alt="Complaint preview" className="mt-3 rounded-2xl" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
