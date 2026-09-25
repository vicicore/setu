import type { ApplicationStepStatus, DocumentStatus, SlaStatus } from "@/lib/api";

export const STATUS_LABEL: Record<ApplicationStepStatus, string> = {
  not_started: "Not started",
  blocked: "Blocked",
  in_progress: "In progress",
  verified: "Verified",
  ready: "Ready",
  rejected: "Rejected",
};

export const STATUS_CLASSES: Record<ApplicationStepStatus, string> = {
  not_started: "bg-slate-100 text-slate-600 border-slate-300",
  blocked: "bg-amber-100 text-amber-800 border-amber-300",
  in_progress: "bg-blue-100 text-blue-800 border-blue-300",
  verified: "bg-emerald-100 text-emerald-800 border-emerald-300",
  ready: "bg-teal-100 text-teal-800 border-teal-300",
  rejected: "bg-red-100 text-red-800 border-red-300",
};

export const SLA_CLASSES: Record<SlaStatus, string> = {
  on_track: "text-emerald-700",
  at_risk: "text-amber-700",
  breached: "text-red-700",
};

export const SLA_LABEL: Record<SlaStatus, string> = {
  on_track: "SLA on track",
  at_risk: "SLA at risk",
  breached: "SLA breached",
};

export const DOC_STATUS_LABEL: Record<DocumentStatus, string> = {
  uploaded: "Uploaded",
  under_review: "Under review",
  verified: "Verified",
  rejected: "Rejected",
  expired: "Expired",
};

export const DOC_STATUS_CLASSES: Record<DocumentStatus, string> = {
  uploaded: "bg-slate-100 text-slate-600 border-slate-300",
  under_review: "bg-blue-100 text-blue-800 border-blue-300",
  verified: "bg-emerald-100 text-emerald-800 border-emerald-300",
  rejected: "bg-red-100 text-red-800 border-red-300",
  expired: "bg-amber-100 text-amber-800 border-amber-300",
};
