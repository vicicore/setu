"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, CitizenProfileView, citizenApi } from "@/lib/api";
import { useCitizenId } from "@/lib/useCitizenId";
import { useLanguage } from "@/lib/LanguageProvider";

export default function ProfilePage() {
  const { t } = useLanguage();
  const [citizenId, setCitizenId] = useCitizenId();
  const [citizenIdInput, setCitizenIdInput] = useState(citizenId);
  const [profile, setProfile] = useState<CitizenProfileView | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [form, setForm] = useState({ full_name: "", district: "", taluka: "", phone: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setNotFound(false);
    setError(null);
    try {
      const p = await citizenApi.getProfile(citizenId);
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
  }, [citizenId, t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await citizenApi.upsertProfile(citizenId, form);
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
          There is no citizen login yet — this is a browser-local identifier standing in for one.
        </p>
      </header>

      <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Citizen ID
        </label>
        <div className="mt-2 flex gap-2">
          <input
            value={citizenIdInput}
            onChange={(e) => setCitizenIdInput(e.target.value)}
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono"
          />
          <button
            onClick={() => setCitizenId(citizenIdInput)}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Switch
          </button>
        </div>
      </section>

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
