"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/lib/LanguageProvider";

const LINKS = [
  { href: "/", labelKey: "nav_home" as const },
  { href: "/services", labelKey: "nav_services" as const },
  { href: "/journeys", labelKey: "nav_journeys" as const },
  { href: "/vault", labelKey: "nav_vault" as const },
  { href: "/profile", labelKey: "nav_profile" as const },
];

export function NavBar() {
  const pathname = usePathname();
  const { language, setLanguage, t } = useLanguage();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link href="/" className="text-lg font-bold tracking-tight text-slate-900">
          OneGov <span className="text-slate-400">/</span> SETU
        </Link>
        <nav className="flex flex-wrap items-center gap-1 text-sm">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-md px-3 py-1.5 font-medium transition ${
                  active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {t(link.labelKey)}
              </Link>
            );
          })}
          <Link
            href="/demo"
            className={`rounded-md border px-3 py-1.5 font-medium transition ${
              pathname === "/demo"
                ? "border-orange-400 bg-orange-50 text-orange-700"
                : "border-orange-300 text-orange-600 hover:bg-orange-50"
            }`}
          >
            {t("nav_demo")}
          </Link>
          <Link
            href="/admin"
            className={`rounded-md px-3 py-1.5 font-medium transition ${
              pathname === "/admin" ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-100"
            }`}
          >
            {t("nav_admin")}
          </Link>
          <div className="ml-2 flex items-center rounded-md border border-slate-200 text-xs">
            <button
              className={`rounded-l-md px-2 py-1 font-medium ${
                language === "en" ? "bg-slate-900 text-white" : "text-slate-500"
              }`}
              onClick={() => setLanguage("en")}
            >
              EN
            </button>
            <button
              className={`rounded-r-md px-2 py-1 font-medium ${
                language === "mr" ? "bg-slate-900 text-white" : "text-slate-500"
              }`}
              onClick={() => setLanguage("mr")}
            >
              मर
            </button>
          </div>
        </nav>
      </div>
    </header>
  );
}
