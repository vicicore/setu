"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ApiError, JourneyDetailView, journeyApi } from "@/lib/api";
import { STATUS_CLASSES, STATUS_LABEL_KEY } from "@/lib/statusStyles";
import { useLanguage } from "@/lib/LanguageProvider";

type ActionName = "consent" | "revoke" | "submit" | "approve" | null;

export default function JourneyDetailPage() {
  const params = useParams<{ id: string }>();
  const applicationId = params.id;
  const { t } = useLanguage();

  const [journey, setJourney] = useState<JourneyDetailView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ActionName>(null);
  const [pendingService, setPendingService] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setJourney(await journeyApi.get(applicationId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    }
  }, [applicationId, t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const runAction = async (
    serviceCode: string,
    action: ActionName,
    fn: () => Promise<JourneyDetailView>,
  ) => {
    setPendingAction(action);
    setPendingService(serviceCode);
    setError(null);
    try {
      setJourney(await fn());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    } finally {
      setPendingAction(null);
      setPendingService(null);
    }
  };

  if (error) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      </main>
    );
  }

  if (!journey) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <p className="text-slate-500">{t("loading")}</p>
      </main>
    );
  }

  const verifiedCount = journey.steps.filter(
    (s) => s.status === "verified" || s.status === "ready",
  ).length;
  const progressPct = Math.round((verifiedCount / journey.steps.length) * 100);

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-4 py-10 sm:px-6">
      <header className="mb-6">
        <span
          className={`inline-block rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
            journey.is_complete
              ? "border-emerald-300 bg-emerald-50 text-emerald-700"
              : "border-blue-300 bg-blue-50 text-blue-700"
          }`}
        >
          {journey.is_complete ? "Complete" : "In progress"}
        </span>
        <h1 className="mt-3 text-3xl font-bold text-slate-900">{journey.life_event_title_en}</h1>
        <p className="text-slate-600">“{journey.goal_statement_en}”</p>
        <p className="mt-1 text-xs text-slate-400 font-mono">{journey.application_id}</p>
      </header>

      <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-slate-700">Overall progress</span>
          <span className="text-slate-500">{progressPct}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-slate-900 transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-lg bg-amber-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              {t("journey_current_blocker")}
            </p>
            <p className="mt-1 text-sm text-amber-900">
              {journey.current_blocker ?? t("journey_none")}
            </p>
          </div>
          <div className="rounded-lg bg-blue-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
              {t("journey_next_action")}
            </p>
            <p className="mt-1 text-sm text-blue-900">{journey.next_action}</p>
          </div>
        </div>
      </section>

      <section className="mb-6 space-y-4">
        {journey.steps.map((step) => {
          const canGrant =
            (step.status === "not_started" || step.status === "ready") && !step.consent?.is_active;
          const canRevoke = step.consent?.is_active;
          const canSubmit =
            (step.status === "not_started" || step.status === "ready") && step.consent?.is_active;
          const canApprove = step.status === "in_progress";

          return (
            <div key={step.service_code} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-slate-900">{step.display_name}</p>
                  <p className="text-xs text-slate-500">
                    {step.department}
                    {step.external_reference && ` · Ref: ${step.external_reference}`}
                  </p>
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
              {step.requires_service_codes.length > 0 && (
                <p className="mt-1 text-xs text-slate-400">
                  ↳ requires {step.requires_service_codes.join(", ")}
                </p>
              )}
              {step.sla_status && (
                <p className="mt-1 text-xs font-medium text-slate-500">
                  SLA: {step.sla_status}
                  {step.sla_due_at && ` · due ${new Date(step.sla_due_at).toLocaleDateString()}`}
                </p>
              )}

              <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                <p className="font-semibold uppercase tracking-wide text-slate-400">
                  {t("consent_title")}
                </p>
                {step.consent ? (
                  <p className="mt-1">
                    Shared with <span className="font-medium">{step.consent.recipient_department}</span>{" "}
                    for &ldquo;{step.consent.purpose}&rdquo; ·{" "}
                    {step.consent.is_active ? (
                      <span className="text-emerald-700">active until{" "}
                        {new Date(step.consent.expires_at).toLocaleDateString()}</span>
                    ) : (
                      <span className="text-red-700">revoked</span>
                    )}
                  </p>
                ) : (
                  <p className="mt-1 text-slate-400">No consent granted yet for this service.</p>
                )}
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <ActionButton
                  label={t("action_grant_consent")}
                  disabled={!canGrant}
                  pending={pendingAction === "consent" && pendingService === step.service_code}
                  onClick={() =>
                    runAction(step.service_code, "consent", () =>
                      journeyApi.grantConsent(
                        applicationId,
                        step.service_code,
                        `Process ${step.display_name}`,
                      ),
                    )
                  }
                />
                <ActionButton
                  label={t("action_revoke_consent")}
                  disabled={!canRevoke}
                  variant="secondary"
                  pending={pendingAction === "revoke" && pendingService === step.service_code}
                  onClick={() =>
                    runAction(step.service_code, "revoke", () =>
                      journeyApi.revokeConsent(applicationId, step.service_code),
                    )
                  }
                />
                <ActionButton
                  label={`${t("action_submit")} to ${step.department}`}
                  disabled={!canSubmit}
                  pending={pendingAction === "submit" && pendingService === step.service_code}
                  onClick={() =>
                    runAction(step.service_code, "submit", () =>
                      journeyApi.submit(applicationId, step.service_code),
                    )
                  }
                />
                <ActionButton
                  label={t("action_approve")}
                  disabled={!canApprove}
                  pending={pendingAction === "approve" && pendingService === step.service_code}
                  onClick={() =>
                    runAction(step.service_code, "approve", () =>
                      journeyApi.approve(applicationId, step.service_code),
                    )
                  }
                />
              </div>
            </div>
          );
        })}
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
    </main>
  );
}

function ActionButton({
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
    "rounded-lg px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40";
  const styles =
    variant === "primary"
      ? "bg-slate-900 text-white hover:bg-slate-700"
      : "border border-slate-300 text-slate-700 hover:bg-slate-50";
  return (
    <button className={`${base} ${styles}`} disabled={disabled || pending} onClick={onClick}>
      {pending ? "…" : label}
    </button>
  );
}
