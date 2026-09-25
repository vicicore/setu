const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type ApplicationStepStatus =
  | "not_started"
  | "blocked"
  | "in_progress"
  | "verified"
  | "ready"
  | "rejected";

export type DocumentStatus = "uploaded" | "under_review" | "verified" | "rejected" | "expired";

export type SlaStatus = "on_track" | "at_risk" | "breached";

export interface DemoCatalogService {
  service_code: string;
  display_name: string;
  department: string;
  requires_service_codes: string[];
}

export interface DemoCatalogView {
  citizen_id: string;
  life_event_code: string;
  citizen_goal_statement_en: string;
  citizen_goal_statement_mr: string;
  services: DemoCatalogService[];
}

export interface DemoStepView {
  service_code: string;
  display_name: string;
  department: string;
  status: ApplicationStepStatus;
  blocked_reason: string | null;
  external_reference: string | null;
  submitted_at: string | null;
  sla_due_at: string | null;
  sla_status: SlaStatus | null;
}

export interface DemoJourneyView {
  application_id: string;
  citizen_id: string;
  steps: DemoStepView[];
  timeline: string[];
  is_complete: boolean;
}

export interface DemoAuditEntryView {
  id: string;
  actor: string;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface DocumentUsedByJourney {
  application_id: string;
  life_event_title_en: string;
  service_code: string;
}

export interface DocumentView {
  id: string;
  citizen_id: string;
  doc_type: string;
  issuer: string | null;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  status: DocumentStatus;
  rejection_reason: string | null;
  url: string;
  created_at: string;
  updated_at: string;
  used_by: DocumentUsedByJourney[];
}

export interface ServiceEligibility {
  service_code: string;
  display_name: string;
  department: string;
  status: ApplicationStepStatus;
  requires_service_codes: string[];
  reasons: string[];
}

export interface EligibilityEvaluateResult {
  life_event_code: string;
  services: ServiceEligibility[];
  overall_ready: boolean;
}

export interface CitizenProfileView {
  citizen_id: string;
  full_name: string;
  dob: string | null;
  district: string | null;
  taluka: string | null;
  phone: string | null;
  email: string | null;
  preferred_language: string;
  profile_completeness_pct: number;
  created_at: string;
  updated_at: string;
}

export interface CitizenProfileUpdate {
  full_name?: string;
  dob?: string;
  district?: string;
  taluka?: string;
  phone?: string;
  preferred_language?: string;
}

export interface LifeEventSummary {
  code: string;
  title_en: string;
  title_mr: string;
  description_en: string;
  description_mr: string;
}

export interface LifeEventService {
  service_code: string;
  display_name: string;
  department: string;
  requires_service_codes: string[];
}

export interface LifeEventDetail extends LifeEventSummary {
  goal_statement_en: string;
  goal_statement_mr: string;
  services: LifeEventService[];
}

export interface JourneyConsentView {
  service_code: string;
  recipient_department: string;
  purpose: string;
  granted_at: string;
  expires_at: string;
  revoked_at: string | null;
  is_active: boolean;
}

export interface JourneyStepView {
  service_code: string;
  display_name: string;
  department: string;
  status: ApplicationStepStatus;
  blocked_reason: string | null;
  requires_service_codes: string[];
  external_reference: string | null;
  submitted_at: string | null;
  sla_due_at: string | null;
  sla_status: SlaStatus | null;
  consent: JourneyConsentView | null;
}

export interface JourneySummaryView {
  application_id: string;
  citizen_id: string;
  life_event_code: string;
  life_event_title_en: string;
  is_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface JourneyDetailView {
  application_id: string;
  citizen_id: string;
  life_event_code: string;
  life_event_title_en: string;
  life_event_title_mr: string;
  goal_statement_en: string;
  steps: JourneyStepView[];
  timeline: string[];
  is_complete: boolean;
  current_blocker: string | null;
  next_action: string;
}

export interface BlockedJourneySummary {
  application_id: string;
  citizen_id: string;
  life_event_code: string;
  blocked_service_codes: string[];
}

export interface AdminMetrics {
  total_journeys: number;
  active_journeys: number;
  complete_journeys: number;
  blocked_journeys: number;
  bottleneck_service_codes: Record<string, number>;
  department_pending_counts: Record<string, number>;
  department_rejected_counts: Record<string, number>;
  sla_at_risk_count: number;
  sla_breached_count: number;
  blocked_journey_details: BlockedJourneySummary[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function handleResponse<T>(path: string, response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `Request to ${path} failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  return handleResponse<T>(path, response);
}

async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body: formData });
  return handleResponse<T>(path, response);
}

export const demoApi = {
  getCatalog: () => request<DemoCatalogView>("/demo/catalog"),
  getJourney: () => request<DemoJourneyView>("/demo/journey"),
  reset: () => request<DemoJourneyView>("/demo/reset", { method: "POST" }),
  grantIncomeConsent: () =>
    request<DemoJourneyView>("/demo/consent/income-certificate", { method: "POST" }),
  submitIncomeCertificate: () =>
    request<DemoJourneyView>("/demo/actions/submit-income-certificate", { method: "POST" }),
  approveIncomeCertificate: () =>
    request<DemoJourneyView>("/demo/actions/approve-income-certificate", { method: "POST" }),
  submitCasteCertificateForReview: () =>
    request<DemoJourneyView>("/demo/actions/submit-caste-certificate-for-review", { method: "POST" }),
  verifyCasteCertificate: () =>
    request<DemoJourneyView>("/demo/actions/verify-caste-certificate", { method: "POST" }),
  getAuditLog: () => request<DemoAuditEntryView[]>("/demo/audit-log"),
};

export const citizenApi = {
  getProfile: (citizenId: string) => request<CitizenProfileView>(`/citizens/${citizenId}/profile`),
  upsertProfile: (citizenId: string, update: CitizenProfileUpdate) =>
    request<CitizenProfileView>(`/citizens/${citizenId}/profile`, {
      method: "PUT",
      body: JSON.stringify(update),
    }),
  getDocuments: (citizenId: string) =>
    request<DocumentView[]>(`/citizens/${citizenId}/documents`),
  uploadDocument: (citizenId: string, file: File, docType: string, issuer?: string) => {
    const form = new FormData();
    form.set("doc_type", docType);
    if (issuer) form.set("issuer", issuer);
    form.set("file", file);
    return uploadRequest<DocumentView>(`/citizens/${citizenId}/documents`, form);
  },
  submitDocumentForReview: (citizenId: string, documentId: string) =>
    request<DocumentView>(`/citizens/${citizenId}/documents/${documentId}/submit-for-review`, {
      method: "POST",
    }),
  verifyDocument: (citizenId: string, documentId: string) =>
    request<DocumentView>(`/citizens/${citizenId}/documents/${documentId}/verify`, {
      method: "POST",
    }),
  rejectDocument: (citizenId: string, documentId: string, reason: string) =>
    request<DocumentView>(`/citizens/${citizenId}/documents/${documentId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  getEligibility: (citizenId: string, lifeEventCode: string) =>
    request<EligibilityEvaluateResult>(`/citizens/${citizenId}/eligibility/${lifeEventCode}`),
};

export const lifeEventApi = {
  list: () => request<LifeEventSummary[]>("/life-events"),
  get: (code: string) => request<LifeEventDetail>(`/life-events/${code}`),
};

export const journeyApi = {
  start: (citizenId: string, lifeEventCode: string) =>
    request<JourneyDetailView>(`/citizens/${citizenId}/journeys`, {
      method: "POST",
      body: JSON.stringify({ life_event_code: lifeEventCode }),
    }),
  listForCitizen: (citizenId: string) =>
    request<JourneySummaryView[]>(`/citizens/${citizenId}/journeys`),
  get: (applicationId: string) => request<JourneyDetailView>(`/journeys/${applicationId}`),
  grantConsent: (applicationId: string, serviceCode: string, purpose: string) =>
    request<JourneyDetailView>(`/journeys/${applicationId}/consent/${serviceCode}`, {
      method: "POST",
      body: JSON.stringify({ purpose }),
    }),
  revokeConsent: (applicationId: string, serviceCode: string) =>
    request<JourneyDetailView>(`/journeys/${applicationId}/consent/${serviceCode}/revoke`, {
      method: "POST",
    }),
  submit: (applicationId: string, serviceCode: string, payload: Record<string, unknown> = {}) =>
    request<JourneyDetailView>(`/journeys/${applicationId}/submit/${serviceCode}`, {
      method: "POST",
      body: JSON.stringify({ payload }),
    }),
  approve: (applicationId: string, serviceCode: string) =>
    request<JourneyDetailView>(`/journeys/${applicationId}/approve/${serviceCode}`, {
      method: "POST",
    }),
};

export const adminApi = {
  getMetrics: () => request<AdminMetrics>("/admin/metrics"),
};
