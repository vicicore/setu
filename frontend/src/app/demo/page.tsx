"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  DemoAuditEntryView,
  DemoCatalogView,
  DemoJourneyView,
  DocumentView,
  EligibilityEvaluateResult,
  citizenApi,
  demoApi,
} from "@/lib/api";
import {
  DOC_STATUS_CLASSES,
  DOC_STATUS_LABEL,
  SLA_CLASSES,
  SLA_LABEL,
  STATUS_CLASSES,
  STATUS_LABEL,
} from "./statusStyles";

type ActionName =
  | "reset"
  | "consent"
  | "submit"
  | "approve"
  | "casteReview"
  | "casteVerify"
  | null;

export default function DemoPage() {
  const [catalog, setCatalog] = useState<DemoCatalogView | null>(null);
  const [journey, setJourney] = useState<DemoJourneyView | null>(null);
  const [documents, setDocuments] = useState<DocumentView[]>([]);
  const [eligibility, setEligibility] = useState<EligibilityEvaluateResult | null>(null);
  const [auditLog, setAuditLog] = useState<DemoAuditEntryView[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<ActionName>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshAll = useCallback(async (citizenId: string, lifeEventCode: string) => {
    // getJourney() lazily seeds the vault on first load (see
    // _reset_vault_and_journey on the backend) — it must resolve before
    // the vault-dependent calls below fire, or they can race ahead and
    // read an empty vault. Not safe to Promise.all with the others.
    const journeyView = await demoApi.getJourney();
    const [docs, elig, audit] = await Promise.all([
      citizenApi.getDocuments(citizenId),
      citizenApi.getEligibility(citizenId, lifeEventCode),
      demoApi.getAuditLog(),
    ]);
    setJourney(journeyView);
    setDocuments(docs);
    setEligibility(elig);
    setAuditLog(audit);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      const catalogView = await demoApi.getCatalog();
      setCatalog(catalogView);
      await refreshAll(catalogView.citizen_id, catalogView.life_event_code);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the SETU backend API.");
    } finally {
      setLoading(false);
    }
  }, [refreshAll]);

  useEffect(() => {
    // Fetching from the FastAPI backend on mount is the documented
    // "synchronize with an external system" case, not derived state —
    // there is no server-rendered initial value to hydrate from since
    // this reads live orchestration state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadAll();
  }, [loadAll]);

  const runAction = async (name: ActionName, fn: () => Promise<DemoJourneyView>) => {
    if (!catalog) return;
    setPendingAction(name);
    setError(null);
    try {
      await fn();
      await refreshAll(catalog.citizen_id, catalog.life_event_code);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed unexpectedly.");
    } finally {
      setPendingAction(null);
    }
  };

  const stepByCode = (code: string) => journey?.steps.find((s) => s.service_code === code);
  const income = stepByCode("income_certificate");
  const scholarship = stepByCode("education_scholarship");
  const casteDoc = documents.find((d) => d.doc_type === "caste_certificate");

  const canGrantConsent = income?.status === "not_started";
  const hasActiveConsent =
    journey !== null &&
    (income?.status === "in_progress" ||
      income?.status === "verified" ||
      auditLog.some((e) => e.action === "consent.granted"));
  const canSubmit = income?.status === "not_started" && hasActiveConsent;
  const canApprove = income?.status === "in_progress";
  const canSubmitCasteForReview = casteDoc?.status === "uploaded";
  const canVerifyCaste = casteDoc?.status === "under_review";

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <span className="inline-block rounded-full border border-orange-300 bg-orange-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-orange-700">
          Demo mode — simulation, not live government data
        </span>
        <h1 className="mt-4 text-3xl font-bold text-slate-900">
          SETU — College Admission + Scholarship
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          One citizen goal, orchestrated across multiple Maharashtra government departments —
          not a list of links to separate portals.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-8 text-center text-slate-500">
          Loading journey state from the backend…
        </div>
      ) : (
        catalog &&
        journey && (
          <div className="space-y-8">
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                1. Citizen goal
              </h2>
              <p className="mt-2 text-lg text-slate-900">“{catalog.citizen_goal_statement_mr}”</p>
              <p className="text-slate-600">“{catalog.citizen_goal_statement_en}”</p>
              <p className="mt-3 text-sm text-slate-500">
                Detected life event: <span className="font-medium text-slate-800">College Admission + Scholarship</span>
              </p>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
                2. Citizen profile &amp; document vault
              </h2>
              <p className="mb-4 text-xs text-slate-500">
                Real vault documents for citizen <span className="font-mono">{catalog.citizen_id}</span> — a
                document being uploaded is not the same as it being verified.
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {documents.map((doc) => (
                  <div key={doc.id} className="rounded-lg border border-slate-200 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-slate-900">{doc.doc_type.replaceAll("_", " ")}</p>
                        <p className="text-xs text-slate-500">{doc.original_filename}</p>
                      </div>
                      <span
                        className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${DOC_STATUS_CLASSES[doc.status]}`}
                      >
                        {DOC_STATUS_LABEL[doc.status]}
                      </span>
                    </div>
                    {doc.doc_type === "caste_certificate" && (
                      <div className="mt-3 flex gap-2">
                        <DemoButton
                          label="Submit for review"
                          disabled={!canSubmitCasteForReview}
                          pending={pendingAction === "casteReview"}
                          onClick={() => runAction("casteReview", demoApi.submitCasteCertificateForReview)}
                        />
                        <DemoButton
                          label="Verify"
                          disabled={!canVerifyCaste}
                          pending={pendingAction === "casteVerify"}
                          onClick={() => runAction("casteVerify", demoApi.verifyCasteCertificate)}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
                3. Eligibility (computed from the vault above, not typed in)
              </h2>
              <p className="mb-4 text-xs text-slate-500">
                Deterministic rules over the same requirement graph the orchestrator uses — no AI in
                this decision.
              </p>
              <div className="space-y-2">
                {eligibility?.services.map((s) => (
                  <div key={s.service_code} className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-slate-700">{s.display_name}</span>
                    <span className="text-right text-xs text-slate-500">{s.reasons[0]}</span>
                    <span
                      className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[s.status]}`}
                    >
                      {STATUS_LABEL[s.status]}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
                4. Required government services &amp; dependency graph
              </h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {journey.steps.map((step) => {
                  const requires =
                    catalog.services.find((s) => s.service_code === step.service_code)
                      ?.requires_service_codes ?? [];
                  return (
                    <div key={step.service_code} className="rounded-lg border border-slate-200 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-medium text-slate-900">{step.display_name}</p>
                          <p className="text-xs text-slate-500">{step.department}</p>
                        </div>
                        <span
                          className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[step.status]}`}
                        >
                          {STATUS_LABEL[step.status]}
                        </span>
                      </div>
                      {step.blocked_reason && (
                        <p className="mt-2 text-xs text-amber-700">⏸ {step.blocked_reason}</p>
                      )}
                      {step.external_reference && (
                        <p className="mt-2 text-xs text-slate-500">Ref: {step.external_reference}</p>
                      )}
                      {step.sla_status && (
                        <p className={`mt-1 text-xs font-medium ${SLA_CLASSES[step.sla_status]}`}>
                          {SLA_LABEL[step.sla_status]}
                        </p>
                      )}
                      {requires.length > 0 && (
                        <p className="mt-2 text-xs text-slate-400">
                          ↳ requires{" "}
                          {requires
                            .map(
                              (code) =>
                                journey.steps.find((s) => s.service_code === code)?.display_name ??
                                code,
                            )
                            .join(", ")}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
                5. Consent &amp; orchestration controls
              </h2>
              <div className="flex flex-wrap gap-3">
                <DemoButton
                  label="Reset demo"
                  variant="secondary"
                  pending={pendingAction === "reset"}
                  onClick={() => runAction("reset", demoApi.reset)}
                />
                <DemoButton
                  label="Grant consent to share data with Revenue"
                  disabled={!canGrantConsent}
                  pending={pendingAction === "consent"}
                  onClick={() => runAction("consent", demoApi.grantIncomeConsent)}
                />
                <DemoButton
                  label="Submit Income Certificate to Revenue connector"
                  disabled={!canSubmit}
                  pending={pendingAction === "submit"}
                  onClick={() => runAction("submit", demoApi.submitIncomeCertificate)}
                />
                <DemoButton
                  label="Simulate Revenue approval (webhook event)"
                  disabled={!canApprove}
                  pending={pendingAction === "approve"}
                  onClick={() => runAction("approve", demoApi.approveIncomeCertificate)}
                />
              </div>
              {scholarship?.status === "ready" && (
                <p className="mt-4 rounded-lg bg-teal-50 px-4 py-3 text-sm font-medium text-teal-800">
                  ✓ Income Certificate verified — Scholarship automatically unlocked. No department
                  hunting, no re-uploaded documents, no separate status tracking.
                </p>
              )}
              {journey.is_complete && (
                <p className="mt-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                  ✓ Every required service for this journey — via the Revenue connector and via the
                  vault — is now verified.
                </p>
              )}
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
                6. Unified journey timeline
              </h2>
              <ol className="space-y-2 text-sm">
                {journey.timeline.map((event, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="text-slate-400">{i + 1}.</span>
                    <span className="text-slate-700">{event}</span>
                  </li>
                ))}
              </ol>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
                7. Audit trail
              </h2>
              {auditLog.length === 0 ? (
                <p className="text-sm text-slate-500">No audit events yet.</p>
              ) : (
                <ul className="space-y-1 text-xs text-slate-500">
                  {auditLog.map((entry) => (
                    <li key={entry.id}>
                      <span className="font-mono">{new Date(entry.created_at).toLocaleTimeString()}</span>{" "}
                      — <span className="font-medium text-slate-700">{entry.actor}</span> {entry.action}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )
      )}
    </main>
  );
}

function DemoButton({
  label,
  onClick,
  disabled,
  pending,
  variant = "primary",
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  pending?: boolean;
  variant?: "primary" | "secondary";
}) {
  const base =
    "rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40";
  const styles =
    variant === "primary"
      ? "bg-slate-900 text-white hover:bg-slate-700"
      : "border border-slate-300 text-slate-700 hover:bg-slate-50";
  return (
    <button
      className={`${base} ${styles}`}
      disabled={disabled || pending}
      onClick={onClick}
    >
      {pending ? "Working…" : label}
    </button>
  );
}
