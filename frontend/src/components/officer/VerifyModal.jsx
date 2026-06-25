import React, { useMemo, useState } from "react";
import { apiStreamRequest, consumeSSE } from "../../utils/sse";

export default function VerifyModal({ complaint, onClose, onComplete }) {
  const [afterPhoto, setAfterPhoto] = useState(null);
  const [location, setLocation] = useState({ lat: null, lon: null, status: "idle" });
  const [streamSteps, setStreamSteps] = useState([]);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState("");

  const afterPreviewUrl = useMemo(() => {
    if (!afterPhoto) {
      return "";
    }
    return URL.createObjectURL(afterPhoto);
  }, [afterPhoto]);

  const handleCaptureLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported in this browser.");
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
        setError("Unable to fetch location. Please allow access.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!afterPhoto || location.lat === null) {
      setError("Please add an after photo and location.");
      return;
    }

    setIsVerifying(true);
    setStreamSteps([]);
    setError("");

    try {
      const formData = new FormData();
      formData.append("latitude", String(location.lat));
      formData.append("longitude", String(location.lon));
      formData.append("after_image", afterPhoto);

      const response = await apiStreamRequest(
        `/complaint/${complaint.complaint_id}/resolve/stream`,
        { method: "POST", body: formData }
      );

      let finalResult = null;
      await consumeSSE(response, {
        step: (payload) => {
          setStreamSteps((prev) => [
            ...prev,
            {
              id: `${payload.step}-${prev.length}`,
              message: payload.message,
              status: payload.status
            }
          ]);
        },
        error: (payload) => {
          throw new Error(payload.message || "Verification failed");
        },
        complete: (payload) => {
          finalResult = payload;
          setStreamSteps((prev) => [
            ...prev,
            {
              id: `complete-${prev.length}`,
              message: payload.message,
              status: payload.is_resolved ? "success" : "warning"
            }
          ]);
        }
      });

      onComplete(finalResult);
    } catch (err) {
      setError(err.message || "Verification failed");
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white shadow-2xl">
        <div className="border-b border-slate-100 px-8 py-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">AI Verification</p>
              <h3 className="mt-1 font-display text-2xl text-slate-900">Submit resolution proof</h3>
              <p className="mt-2 text-sm text-slate-500">
                Upload a photo from the site after fixing the issue. The system verifies location and visual
                resolution.
              </p>
            </div>
            <button type="button" className="btn-secondary shrink-0" onClick={onClose} disabled={isVerifying}>
              Close
            </button>
          </div>
        </div>

        <form className="space-y-5 px-8 py-6" onSubmit={handleSubmit}>
          <div className="rounded-2xl bg-slate-50 p-4 text-sm">
            <p className="font-semibold text-slate-700">{complaint.description}</p>
            <p className="mt-1 font-mono text-xs text-slate-400">{complaint.complaint_id}</p>
          </div>

          <label className="block text-sm font-semibold text-slate-700">
            After photo
            <input
              type="file"
              accept="image/*"
              className="mt-2 block w-full text-sm text-slate-600"
              onChange={(event) => setAfterPhoto(event.target.files?.[0] || null)}
              required
              disabled={isVerifying}
            />
          </label>

          {afterPreviewUrl && (
            <img src={afterPreviewUrl} alt="After preview" className="h-44 w-full rounded-2xl object-cover" />
          )}

          <div className="rounded-2xl border border-dashed border-slate-200 p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-slate-700">Resolution location</p>
                <p className="text-xs text-slate-500">
                  {location.lat !== null
                    ? `Lat ${location.lat.toFixed(5)}, Lon ${location.lon.toFixed(5)}`
                    : "Capture GPS at the complaint site"}
                </p>
              </div>
              <button
                type="button"
                className="btn-secondary shrink-0"
                onClick={handleCaptureLocation}
                disabled={location.status === "loading" || isVerifying}
              >
                {location.status === "loading" ? "Fetching…" : "Use GPS"}
              </button>
            </div>
          </div>

          {streamSteps.length > 0 && (
            <div className="rounded-2xl bg-blue-50/50 p-4 ring-1 ring-blue-100">
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">Live verification</p>
              <ul className="mt-3 space-y-2">
                {streamSteps.map((step) => (
                  <li
                    key={step.id}
                    className={`rounded-xl px-3 py-2 text-sm ${
                      step.status === "success"
                        ? "bg-emerald-50 text-emerald-700"
                        : step.status === "warning"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-white text-slate-700"
                    }`}
                  >
                    {step.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

          <button className="btn w-full" type="submit" disabled={isVerifying || !afterPhoto || location.lat === null}>
            {isVerifying ? "Running verification…" : "Run AI verification"}
          </button>
        </form>
      </div>
    </div>
  );
}
