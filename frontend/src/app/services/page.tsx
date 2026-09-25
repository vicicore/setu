"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, LifeEventSummary, journeyApi, lifeEventApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useLanguage } from "@/lib/LanguageProvider";

export default function ServicesPage() {
  const router = useRouter();
  const { language, t } = useLanguage();
  const { citizenId, token, isLoggedIn } = useAuth();
  const [lifeEvents, setLifeEvents] = useState<LifeEventSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [startingCode, setStartingCode] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLifeEvents(await lifeEventApi.list());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    }
  }, [t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const startJourney = async (code: string) => {
    if (!isLoggedIn || !citizenId) {
      router.push("/login");
      return;
    }
    setStartingCode(code);
    setError(null);
    try {
      const journey = await journeyApi.start(citizenId, code, token ?? undefined);
      router.push(`/journeys/${journey.application_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
      setStartingCode(null);
    }
  };

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">{t("home_tell_us")}</h1>
        <p className="mt-2 text-slate-600">
          Every life event below is a real orchestration graph in SETU — pick one to start a
          journey.
          {!isLoggedIn && (
            <>
              {" "}
              <Link href="/login" className="font-medium underline">
                Log in
              </Link>{" "}
              first to start one.
            </>
          )}
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {!lifeEvents ? (
        <p className="text-slate-500">{t("loading")}</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {lifeEvents.map((event) => (
            <div
              key={event.code}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div>
                <h2 className="font-semibold text-slate-900">
                  {language === "mr" ? event.title_mr : event.title_en}
                </h2>
                <p className="mt-2 text-sm text-slate-600">
                  {language === "mr" ? event.description_mr : event.description_en}
                </p>
              </div>
              <button
                onClick={() => startJourney(event.code)}
                disabled={startingCode === event.code}
                className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-40"
              >
                {startingCode === event.code ? t("loading") : t("action_start_journey")}
              </button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
