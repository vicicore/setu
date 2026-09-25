"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, JourneyDetailView, journeyApi, lifeEventApi } from "@/lib/api";
import { STATUS_CLASSES, STATUS_LABEL_KEY } from "@/lib/statusStyles";
import { useLanguage } from "@/lib/LanguageProvider";
import { DemoButton } from "./DemoButton";

const LIFE_EVENT_CODE = "start_small_business";
// A fixed demo citizen so this panel behaves predictably in a live
// judge session, without needing a second demo-specific endpoint set —
// this scenario proves the *generic* /journeys API is real, not a
// second copy of the College Admission implementation.
const DEMO_BUSINESS_CITIZEN_ID = "demo-citizen-anil-jadhav";

type ActionName = "start" | "consent" | "submit" | "approve" | null;

export function SmallBusinessPanel() {
  const { t } = useLanguage();
  const [journey, setJourney] = useState<JourneyDetailView | null>(null);
  const [goalStatement, setGoalStatement] = useState<{ en: string; mr: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<ActionName>(null);
  const [pendingService, setPendingService] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadExisting = useCallback(async () => {
    try {
      const meta = await lifeEventApi.get(LIFE_EVENT_CODE);
      setGoalStatement({ en: meta.goal_statement_en, mr: meta.goal_statement_mr });
      const existing = await journeyApi.listForCitizen(DEMO_BUSINESS_CITIZEN_ID);
      if (existing.length > 0) {
        const detail = await journeyApi.get(existing[existing.length - 1].application_id);
        setJourney(detail);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the SETU backend API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadExisting();
  }, [loadExisting]);

  const startNewJourney = async () => {
    setPendingAction("start");
    setError(null);
    try {
      const detail = await journeyApi.start(DEMO_BUSINESS_CITIZEN_ID, LIFE_EVENT_CODE);
      setJourney(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the journey.");
    } finally {
      setPendingAction(null);
    }
  };

  const runStepAction = async (
    serviceCode: string,
    action: ActionName,
    fn: (applicationId: string) => Promise<JourneyDetailView>,
  ) => {
    if (!journey) return;
    setPendingAction(action);
    setPendingService(serviceCode);
    setError(null);
    try {
      const detail = await fn(journey.application_id);
      setJourney(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed unexpectedly.");
    } finally {
      setPendingAction(null);
      setPendingService(null);
    }
  };

  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-8 text-center text-slate-500">
        {t("loading")}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Citizen goal
        </h2>
        {goalStatement && (
          <>
            <p className="mt-2 text-lg text-slate-900">“{goalStatement.mr}”</p>
            <p className="text-slate-600">“{goalStatement.en}”</p>
          </>
        )}
        <p className="mt-3 text-xs text-slate-500">
          This scenario proves SETU&apos;s orchestrator is generic: the same journeys API, the
          same event-processing path, and three different mock connectors (Labour, Urban
          Development, Finance) — nothing about College Admission is hardcoded into it.
        </p>
        <div className="mt-4">
          <DemoButton
            label={journey ? "Start a new Small Business journey" : t("action_start_journey")}
            pending={pendingAction === "start"}
            onClick={startNewJourney}
          />
        </div>
      </section>

      {journey && (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Required services &amp; consent-driven controls
            </h2>
            <div className="space-y-4">
              {journey.steps.map((step) => {
                const canGrant =
                  (step.status === "not_started" || step.status === "ready") &&
                  !step.consent?.is_active;
                const canSubmit =
                  (step.status === "not_started" || step.status === "ready") &&
                  step.consent?.is_active;
                const canApprove = step.status === "in_progress";
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
                    {step.requires_service_codes.length > 0 && (
                      <p className="mt-1 text-xs text-slate-400">
                        ↳ requires{" "}
                        {step.requires_service_codes
                          .map(
                            (code) =>
                              journey.steps.find((s) => s.service_code === code)?.display_name ??
                              code,
                          )
                          .join(", ")}
                      </p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <DemoButton
                        label={t("action_grant_consent")}
                        disabled={!canGrant}
                        pending={pendingAction === "consent" && pendingService === step.service_code}
                        onClick={() =>
                          runStepAction(step.service_code, "consent", (id) =>
                            journeyApi.grantConsent(
                              id,
                              step.service_code,
                              `Process ${step.display_name}`,
                            ),
                          )
                        }
                      />
                      <DemoButton
                        label={`${t("action_submit")} to ${step.department}`}
                        disabled={!canSubmit}
                        pending={pendingAction === "submit" && pendingService === step.service_code}
                        onClick={() =>
                          runStepAction(step.service_code, "submit", (id) =>
                            journeyApi.submit(id, step.service_code),
                          )
                        }
                      />
                      <DemoButton
                        label={t("action_approve")}
                        disabled={!canApprove}
                        pending={pendingAction === "approve" && pendingService === step.service_code}
                        onClick={() =>
                          runStepAction(step.service_code, "approve", (id) =>
                            journeyApi.approve(id, step.service_code),
                          )
                        }
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            {journey.is_complete && (
              <p className="mt-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                ✓ Business registration, local NOC and GST registration are all verified — this
                journey is complete.
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
        </>
      )}
    </div>
  );
}
