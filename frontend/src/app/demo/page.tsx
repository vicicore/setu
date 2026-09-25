"use client";

import { useState } from "react";
import { CollegeAdmissionPanel } from "./CollegeAdmissionPanel";
import { SmallBusinessPanel } from "./SmallBusinessPanel";

type Scenario = "college" | "business";

export default function DemoPage() {
  const [scenario, setScenario] = useState<Scenario>("college");

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <span className="inline-block rounded-full border border-orange-300 bg-orange-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-orange-700">
          Judge mode — simulation, not live government data
        </span>
        <h1 className="mt-4 text-3xl font-bold text-slate-900">SETU Judge Demo</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Two real orchestrated journeys, driving actual backend state — not a presentation
          animation. Every control below calls the FastAPI backend.
        </p>

        <div className="mt-6 flex gap-2">
          <ScenarioTab
            active={scenario === "college"}
            onClick={() => setScenario("college")}
            label="1. College Admission + Scholarship"
          />
          <ScenarioTab
            active={scenario === "business"}
            onClick={() => setScenario("business")}
            label="2. Start a Small Business"
          />
        </div>
      </header>

      {scenario === "college" ? <CollegeAdmissionPanel /> : <SmallBusinessPanel />}
    </main>
  );
}

function ScenarioTab({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
        active
          ? "bg-slate-900 text-white"
          : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
      }`}
    >
      {label}
    </button>
  );
}
