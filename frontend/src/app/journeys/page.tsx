"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, JourneySummaryView, journeyApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useLanguage } from "@/lib/LanguageProvider";

export default function JourneysPage() {
  const { t } = useLanguage();
  const { citizenId, token, isLoggedIn } = useAuth();
  const [journeys, setJourneys] = useState<JourneySummaryView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!citizenId) return;
    try {
      setJourneys(await journeyApi.listForCitizen(citizenId, token ?? undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    }
  }, [citizenId, token, t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  if (!isLoggedIn || !citizenId) {
    return (
      <main className="mx-auto min-h-screen max-w-4xl px-4 py-10 sm:px-6">
        <p className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">
          <Link href="/login" className="font-medium underline">
            Log in
          </Link>{" "}
          to view your journeys.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">{t("nav_journeys")}</h1>
        <p className="mt-2 text-slate-600">
          Journeys for citizen <span className="font-mono text-xs">{citizenId}</span>. Start a new
          one from <Link href="/services" className="underline">Discover Services</Link>.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {!journeys ? (
        <p className="text-slate-500">{t("loading")}</p>
      ) : journeys.length === 0 ? (
        <p className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500">
          No journeys yet.
        </p>
      ) : (
        <div className="space-y-3">
          {journeys.map((j) => (
            <Link
              key={j.application_id}
              href={`/journeys/${j.application_id}`}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300"
            >
              <div>
                <p className="font-medium text-slate-900">{j.life_event_title_en}</p>
                <p className="text-xs text-slate-500">
                  Started {new Date(j.created_at).toLocaleDateString()}
                </p>
              </div>
              <span
                className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
                  j.is_complete
                    ? "border-emerald-300 bg-emerald-100 text-emerald-800"
                    : "border-blue-300 bg-blue-100 text-blue-800"
                }`}
              >
                {j.is_complete ? "Complete" : "In progress"}
              </span>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
