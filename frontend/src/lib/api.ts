const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type ApplicationStepStatus =
  | "not_started"
  | "blocked"
  | "in_progress"
  | "verified"
  | "ready"
  | "rejected";

export type SlaStatus = "on_track" | "at_risk" | "breached";

export interface DemoCatalogService {
  service_code: string;
  display_name: string;
  department: string;
  depends_on_service_code: string | null;
}

export interface DemoCatalogView {
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

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `Request to ${path} failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
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
  getAuditLog: () => request<DemoAuditEntryView[]>("/demo/audit-log"),
};
