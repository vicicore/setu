"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useLanguage } from "@/lib/LanguageProvider";

export default function LoginPage() {
  const { t } = useLanguage();
  const router = useRouter();
  const { login, isLoggedIn } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoggedIn) router.replace("/services");
  }, [isLoggedIn, router]);

  const submit = async () => {
    if (!identifier.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(identifier.trim());
      router.push("/services");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold text-slate-900">{t("login_title")}</h1>
      <p className="mt-2 text-sm text-slate-600">
        This is real, server-verified authentication — not a free-text citizen ID. It is not
        Aadhaar or OTP-based in this prototype (see docs/DECISIONS.md).
      </p>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("login_identifier_label")}
        </label>
        <input
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          placeholder="e.g. 9876543210"
        />
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        <button
          onClick={submit}
          disabled={submitting || !identifier.trim()}
          className="mt-4 w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-40"
        >
          {submitting ? t("loading") : t("login_button")}
        </button>
      </div>
    </main>
  );
}
