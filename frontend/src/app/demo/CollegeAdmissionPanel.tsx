"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  DemoAuditEntryView,
  DemoCatalogView,
  DemoJourneyView,
  DocumentView,
  EligibilityEvaluateResult,
  authApi,
  citizenApi,
  demoApi,
} from "@/lib/api";
import { DOC_STATUS_CLASSES, DOC_STATUS_LABEL_KEY, STATUS_CLASSES, STATUS_LABEL_KEY } from "@/lib/statusStyles";
import { useLanguage } from "@/lib/LanguageProvider";
import { DemoButton } from "./DemoButton";

type ActionName =
  | "reset"
  | "consent"
  | "submit"
  | "approve"
  | "casteReview"
  | "casteVerify"
  | null;

/** The original, judge-approved College Admission + Scholarship demo.
 * Backed by the /demo/* endpoints — unchanged since Phase 5, per the
 * explicit instruction to keep this flow fully deterministic. */
export function CollegeAdmissionPanel() {
  const { t } = useLanguage();
  const [catalog, setCatalog] = useState<DemoCatalogView | null>(null);
  const [journey, setJourney] = useState<DemoJourneyView | null>(null);
  const [documents, setDocuments] = useState<DocumentView[]>([]);
  const [eligibility, setEligibility] = useState<EligibilityEvaluateResult | null>(null);
  const [auditLog, setAuditLog] = useState<DemoAuditEntryView[]>([]);
  const [demoToken, setDemoToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<ActionName>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshAll = useCallback(
    async (citizenId: string, lifeEventCode: string, token: string) => {
      const journeyView = await demoApi.getJourney();
      const [docs, elig, audit] = await Promise.all([
        citizenApi.getDocuments(citizenId, token),
        citizenApi.getEligibility(citizenId, lifeEventCode, token),
        demoApi.getAuditLog(),
      ]);
      setJourney(journeyView);
      setDocuments(docs);
      setEligibility(elig);
      setAuditLog(audit);
    },
    [],
  );

  const loadAll = useCallback(async () => {
    try {
      const catalogView = await demoApi.getCatalog();
      setCatalog(catalogView);
      // Judge mode authenticates silently as the fixed demo identity —
      // a real bearer token from the same auth path a citizen uses, not
      // a bypass, so /citizens/* and /journeys/* calls below stay
      // genuinely authorized rather than trusting a client-supplied id.
      const session = await authApi.login(catalogView.login_identifier);
      setDemoToken(session.token);
      await refreshAll(catalogView.citizen_id, catalogView.life_event_code, session.token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the SETU backend API.");
    } finally {
      setLoading(false);
    }
  }, [refreshAll]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadAll();
  }, [loadAll]);

  const runAction = async (name: ActionName, fn: () => Promise<DemoJourneyView>) => {
    if (!catalog || !demoToken) return;
    setPendingAction(name);
    setError(null);
    try {
      await fn();
      await refreshAll(catalog.citizen_id, catalog.life_event_code, demoToken);
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

  if (error) {
    return (
      <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
        {error}
      </div>
    );
  }

  if (loading || !catalog || !journey) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-8 text-center text-slate-500">
        {t("loading")}
      </div>
    );
  }

  return (
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
                  {t(DOC_STATUS_LABEL_KEY[doc.status])}
                </span>
              </div>
              {doc.doc_type === "caste_certificate" && (
                <div className="mt-3 flex gap-2">
                  <DemoButton
                    label={t("action_submit_for_review")}
                    disabled={!canSubmitCasteForReview}
                    pending={pendingAction === "casteReview"}
                    onClick={() => runAction("casteReview", demoApi.submitCasteCertificateForReview)}
                  />
                  <DemoButton
                    label={t("action_verify")}
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
                {t(STATUS_LABEL_KEY[s.status])}
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
                    {t(STATUS_LABEL_KEY[step.status])}
                  </span>
                </div>
                {step.blocked_reason && (
                  <p className="mt-2 text-xs text-amber-700">⏸ {step.blocked_reason}</p>
                )}
                {step.external_reference && (
                  <p className="mt-2 text-xs text-slate-500">Ref: {step.external_reference}</p>
                )}
                {step.sla_status && (
                  <p className="mt-1 text-xs font-medium text-slate-500">SLA: {step.sla_status}</p>
                )}
                {requires.length > 0 && (
                  <p className="mt-2 text-xs text-slate-400">
                    ↳ requires{" "}
                    {requires
                      .map(
                        (code) =>
                          journey.steps.find((s) => s.service_code === code)?.display_name ?? code,
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
            label={t("action_reset_demo")}
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
          {t("journey_timeline")}
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
  );
}
