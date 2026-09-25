"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, CitizenProfileView, citizenApi } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useLanguage } from "@/lib/LanguageProvider";

export default function ProfilePage() {
  const { t } = useLanguage();
  const { citizenId, token, isLoggedIn } = useAuth();
  const [profile, setProfile] = useState<CitizenProfileView | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [form, setForm] = useState({ full_name: "", district: "", taluka: "", phone: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!citizenId) return;
    setNotFound(false);
    setError(null);
    try {
      const p = await citizenApi.getProfile(citizenId, token ?? undefined);
      setProfile(p);
      setForm({
        full_name: p.full_name,
        district: p.district ?? "",
        taluka: p.taluka ?? "",
        phone: p.phone ?? "",
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
        setProfile(null);
      } else {
        setError(err instanceof ApiError ? err.message : t("error_generic"));
      }
    }
  }, [citizenId, token, t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  if (!isLoggedIn || !citizenId) {
    return (
      <main className="mx-auto min-h-screen max-w-2xl px-4 py-10 sm:px-6">
        <p className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">
          <Link href="/login" className="font-medium underline">
            Log in
          </Link>{" "}
          to view your profile.
        </p>
      </main>
    );
  }

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await citizenApi.upsertProfile(citizenId, form, token ?? undefined);
      setProfile(updated);
      setNotFound(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="mx-auto min-h-screen max-w-2xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">{t("nav_profile")}</h1>
        <p className="mt-2 text-sm text-slate-600">
          Logged in as <span className="font-mono text-xs">{citizenId}</span>.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {notFound && (
          <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            No profile yet for this citizen — fill in the form below to create one.
          </p>
        )}
        {profile && (
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Profile completeness
            </span>
            <span className="text-sm font-medium text-slate-700">
              {profile.profile_completeness_pct}%
            </span>
          </div>
        )}
        <div className="space-y-3">
          <Field label="Full name" value={form.full_name} onChange={(v) => setForm({ ...form, full_name: v })} />
          <Field label="District" value={form.district} onChange={(v) => setForm({ ...form, district: v })} />
          <Field label="Taluka" value={form.taluka} onChange={(v) => setForm({ ...form, taluka: v })} />
          <Field label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="mt-5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-40"
        >
          {saving ? t("loading") : "Save profile"}
        </button>
      </section>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
    </label>
  );
}
