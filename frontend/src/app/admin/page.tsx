"use client";

import { useCallback, useEffect, useState } from "react";
import { AdminMetrics, ApiError, adminApi } from "@/lib/api";

export default function AdminPage() {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setMetrics(await adminApi.getMetrics());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the SETU backend API.");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  if (error) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      </main>
    );
  }

  if (!metrics) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <p className="text-slate-500">Loading…</p>
      </main>
    );
  }

  const bottlenecks = Object.entries(metrics.bottleneck_service_codes).sort((a, b) => b[1] - a[1]);
  const pending = Object.entries(metrics.department_pending_counts);
  const rejected = Object.entries(metrics.department_rejected_counts);

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <span className="inline-block rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          Real backend metrics — computed from actual application state, refresh to update
        </span>
        <h1 className="mt-4 text-3xl font-bold text-slate-900">Government Operations</h1>
        <p className="mt-2 text-slate-600">
          Every number below comes from walking real journeys through the same dependency graph
          and SLA logic every citizen screen uses — nothing here is fabricated.
        </p>
      </header>

      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Total journeys" value={metrics.total_journeys} />
        <StatTile label="Active" value={metrics.active_journeys} />
        <StatTile label="Complete" value={metrics.complete_journeys} tone="good" />
        <StatTile label="Blocked" value={metrics.blocked_journeys} tone={metrics.blocked_journeys > 0 ? "warn" : "good"} />
        <StatTile label="SLA at risk" value={metrics.sla_at_risk_count} tone={metrics.sla_at_risk_count > 0 ? "warn" : "good"} />
        <StatTile label="SLA breached" value={metrics.sla_breached_count} tone={metrics.sla_breached_count > 0 ? "bad" : "good"} />
      </div>

      <section className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Where are citizens getting stuck?
        </h2>
        <p className="mb-4 text-xs text-slate-500">
          Service codes appearing as a blocker across active journeys — this is why orchestration
          matters: a single stuck prerequisite blocks every downstream service that requires it.
        </p>
        {bottlenecks.length === 0 ? (
          <p className="text-sm text-slate-500">No blocked journeys right now.</p>
        ) : (
          <div className="space-y-2">
            {bottlenecks.map(([code, count]) => (
              <div key={code} className="flex items-center justify-between text-sm">
                <span className="text-slate-700">{code.replaceAll("_", " ")}</span>
                <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                  {count} journey{count === 1 ? "" : "s"} blocked here
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Department pending workload
          </h2>
          {pending.length === 0 ? (
            <p className="text-sm text-slate-500">Nothing in progress.</p>
          ) : (
            <ul className="space-y-1 text-sm text-slate-700">
              {pending.map(([dept, count]) => (
                <li key={dept} className="flex justify-between">
                  <span>{dept}</span>
                  <span className="font-medium">{count}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Department rejections
          </h2>
          {rejected.length === 0 ? (
            <p className="text-sm text-slate-500">No rejections recorded.</p>
          ) : (
            <ul className="space-y-1 text-sm text-slate-700">
              {rejected.map(([dept, count]) => (
                <li key={dept} className="flex justify-between">
                  <span>{dept}</span>
                  <span className="font-medium">{count}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Blocked journeys
        </h2>
        {metrics.blocked_journey_details.length === 0 ? (
          <p className="text-sm text-slate-500">No blocked journeys.</p>
        ) : (
          <div className="space-y-2">
            {metrics.blocked_journey_details.map((j) => (
              <div key={j.application_id} className="rounded-lg border border-slate-100 p-3 text-sm">
                <p className="font-mono text-xs text-slate-400">{j.application_id}</p>
                <p className="text-slate-700">
                  {j.citizen_id} · blocked on {j.blocked_service_codes.join(", ")}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function StatTile({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  const toneClass = {
    neutral: "text-slate-900",
    good: "text-emerald-700",
    warn: "text-amber-700",
    bad: "text-red-700",
  }[tone];
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-center shadow-sm">
      <p className={`text-2xl font-bold ${toneClass}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-500">{label}</p>
    </div>
  );
}
