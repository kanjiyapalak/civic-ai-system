import { API_BASE } from "../api";

export const STATUS_CONFIG = {
  PENDING: {
    label: "Pending",
    badge: "bg-amber-100 text-amber-800 ring-amber-200",
    card: "border-l-4 border-l-amber-400",
    header: "bg-amber-50",
    icon: "⏳",
    description: "Awaiting your acceptance"
  },
  IN_PROGRESS: {
    label: "In Progress",
    badge: "bg-blue-100 text-blue-800 ring-blue-200",
    card: "border-l-4 border-l-blue-500",
    header: "bg-blue-50",
    icon: "🔧",
    description: "Currently being resolved"
  },
  COMPLETED: {
    label: "Completed",
    badge: "bg-emerald-100 text-emerald-800 ring-emerald-200",
    card: "border-l-4 border-l-emerald-500",
    header: "bg-emerald-50",
    icon: "✓",
    description: "Verified and closed"
  },
  DUPLICATE: {
    label: "Linked",
    badge: "bg-slate-100 text-slate-700 ring-slate-200",
    card: "border-l-4 border-l-slate-400",
    header: "bg-slate-50",
    icon: "🔗",
    description: "Linked to an existing complaint"
  },
  REJECTED: {
    label: "Not accepted",
    badge: "bg-red-100 text-red-800 ring-red-200",
    card: "border-l-4 border-l-red-400",
    header: "bg-red-50",
    icon: "✕",
    description: "No issue detected in photo"
  }
};

export const CITIZEN_STATUS_HINTS = {
  PENDING: "Your complaint is queued — an officer will be assigned soon.",
  IN_PROGRESS: "An officer is actively working on your complaint.",
  COMPLETED: "Your complaint has been verified and resolved.",
  DUPLICATE: "This report was linked to a nearby existing complaint.",
  REJECTED: "This submission was not accepted. Only visible public civic issues (roads, parks, public infrastructure) are accepted — not private home or office problems."
};

export function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

export function formatRelativeDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return formatDate(value);
  }
  const diffMs = Date.now() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) {
    return "Just now";
  }
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    return `${diffDays}d ago`;
  }
  return date.toLocaleDateString();
}

export function resolveImageUrl(value) {
  if (!value) {
    return "";
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value;
  }
  return `${API_BASE}/${value.replace(/^\//, "")}`;
}

export function filterComplaints(items, { status, search }) {
  let filtered = items;

  if (status && status !== "all") {
    filtered = filtered.filter((item) => (item.status || "PENDING") === status);
  }

  const query = (search || "").trim().toLowerCase();
  if (query) {
    filtered = filtered.filter(
      (item) =>
        (item.complaint_id || "").toLowerCase().includes(query) ||
        (item.description || "").toLowerCase().includes(query) ||
        (item.issue_type || "").toLowerCase().includes(query) ||
        (item.department || "").toLowerCase().includes(query) ||
        (item.ward || "").toLowerCase().includes(query) ||
        (item.officer || "").toLowerCase().includes(query) ||
        (item.citizen || "").toLowerCase().includes(query)
    );
  }

  return filtered;
}

export function getStatusConfig(status) {
  return STATUS_CONFIG[status] || {
    label: status || "Unknown",
    badge: "bg-slate-100 text-slate-700 ring-slate-200",
    card: "border-l-4 border-l-slate-300",
    header: "bg-slate-50",
    icon: "•",
    description: ""
  };
}
