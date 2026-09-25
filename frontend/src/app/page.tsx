"use client";

import Link from "next/link";
import { useLanguage } from "@/lib/LanguageProvider";

export default function Home() {
  const { t } = useLanguage();

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-14 sm:px-6">
      <header className="mb-12 text-center">
        <span className="inline-block rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          Government of Maharashtra · SIH260129
        </span>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">
          OneGov / SETU (सेतु)
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">{t("home_tagline")}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/services"
            className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            {t("home_tell_us")}
          </Link>
          <Link
            href="/demo"
            className="rounded-lg border border-orange-300 px-5 py-2.5 text-sm font-medium text-orange-700 transition hover:bg-orange-50"
          >
            {t("nav_demo")}
          </Link>
        </div>
      </header>

      <section className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t("home_how_it_works")}
        </h2>
        <div className="grid grid-cols-1 gap-4 text-sm text-slate-600 sm:grid-cols-5">
          {[
            "Citizen states a goal",
            "SETU finds required services",
            "Checks what's already verified",
            "Requests consent, coordinates departments",
            "One unified journey, tracked to completion",
          ].map((step, i) => (
            <div key={step} className="flex flex-col items-center text-center">
              <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                {i + 1}
              </div>
              {step}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          How SETU is built
        </h2>
        <div className="mb-6 flex flex-wrap items-center justify-center gap-2 text-xs font-medium text-slate-600">
          {["Citizen", "OneGov UI", "Profile + Consent", "Service Orchestrator", "Connector / Adapter Layer", "Government Departments"].map(
            (node, i, arr) => (
              <span key={node} className="flex items-center gap-2">
                <span className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1.5">{node}</span>
                {i < arr.length - 1 && <span className="text-slate-300">→</span>}
              </span>
            ),
          )}
        </div>
        <p className="mx-auto max-w-2xl text-center text-base font-medium text-slate-900">
          {t("home_central_message")}
        </p>
        <div className="mx-auto mt-5 grid max-w-2xl grid-cols-1 gap-2 text-sm text-slate-600 sm:grid-cols-2">
          <p>• Existing portals remain authoritative.</p>
          <p>• SETU orchestrates, it doesn&apos;t replace.</p>
          <p>• Connectors isolate each department&apos;s own API.</p>
          <p>• Consent controls every data share.</p>
          <p>• The orchestrator manages dependencies.</p>
          <p>• One timeline hides departmental fragmentation.</p>
        </div>
      </section>
    </main>
  );
}
