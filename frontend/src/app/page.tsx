import Link from "next/link";

const LIFE_EVENTS = [
  {
    code: "college_admission_scholarship",
    title: "College Admission + Scholarship",
    description:
      "Apply for an engineering admission scholarship — SETU checks your verified documents, requests consent, and coordinates Revenue and Higher Education for you.",
    href: "/demo",
    status: "live" as const,
  },
  {
    code: "start_small_business",
    title: "Starting a Small Business",
    description: "Shop & establishment registration, local NOC and GST — one coordinated journey.",
    href: null,
    status: "coming_soon" as const,
  },
  {
    code: "farmer_support",
    title: "Farmer Support / Agricultural Benefit",
    description: "Agricultural benefit schemes tied to land records and identity.",
    href: null,
    status: "coming_soon" as const,
  },
  {
    code: "family_civil_certificates",
    title: "Family / Civil Certificates",
    description: "Birth, death, marriage and residence certificates for a household.",
    href: null,
    status: "coming_soon" as const,
  },
];

export default function Home() {
  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-14 sm:px-6">
      <header className="mb-12 text-center">
        <span className="inline-block rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          Government of Maharashtra · SIH260129
        </span>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">
          OneGov / SETU (सेतु)
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">
          Citizens shouldn&apos;t have to know which department provides a service. Tell SETU what
          you need — it discovers the required government services, reuses what&apos;s already
          verified, and coordinates the rest.
        </p>
      </header>

      <section className="mb-12 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          How SETU works
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

      <section>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Tell us what you need
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {LIFE_EVENTS.map((event) => (
            <div
              key={event.code}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="font-semibold text-slate-900">{event.title}</h3>
                  {event.status === "coming_soon" && (
                    <span className="whitespace-nowrap rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                      Coming soon
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-600">{event.description}</p>
              </div>
              {event.href ? (
                <Link
                  href={event.href}
                  className="mt-4 inline-block rounded-lg bg-slate-900 px-4 py-2 text-center text-sm font-medium text-white transition hover:bg-slate-700"
                >
                  Start this journey
                </Link>
              ) : (
                <button
                  disabled
                  className="mt-4 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-400"
                >
                  Not yet available
                </button>
              )}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
