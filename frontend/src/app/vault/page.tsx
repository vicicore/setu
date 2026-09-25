"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ApiError, DocumentView, citizenApi } from "@/lib/api";
import { DOC_STATUS_CLASSES, DOC_STATUS_LABEL_KEY } from "@/lib/statusStyles";
import { useAuth } from "@/lib/useAuth";
import { useLanguage } from "@/lib/LanguageProvider";

type ActionName = "upload" | "review" | "verify" | "reject" | null;

export default function VaultPage() {
  const { t } = useLanguage();
  const { citizenId, token, isLoggedIn } = useAuth();
  const [documents, setDocuments] = useState<DocumentView[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ActionName>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [docType, setDocType] = useState("supplementary_document");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    if (!citizenId) return;
    try {
      setDocuments(await citizenApi.getDocuments(citizenId, token ?? undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    }
  }, [citizenId, token, t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const handleUpload = async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file || !citizenId) return;
    setPendingAction("upload");
    setError(null);
    try {
      await citizenApi.uploadDocument(citizenId, file, docType, undefined, token ?? undefined);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    } finally {
      setPendingAction(null);
    }
  };

  const runDocAction = async (documentId: string, action: ActionName, fn: () => Promise<DocumentView>) => {
    setPendingAction(action);
    setPendingId(documentId);
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("error_generic"));
    } finally {
      setPendingAction(null);
      setPendingId(null);
    }
  };

  if (!isLoggedIn || !citizenId) {
    return (
      <main className="mx-auto min-h-screen max-w-4xl px-4 py-10 sm:px-6">
        <p className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">
          <Link href="/login" className="font-medium underline">
            Log in
          </Link>{" "}
          to view your documents.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">{t("nav_vault")}</h1>
        <p className="mt-2 text-slate-600">
          Documents for citizen <span className="font-mono text-xs">{citizenId}</span>. Real
          lifecycle: uploaded → under review → verified or rejected.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t("action_upload")}
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            placeholder="document type (e.g. income_certificate)"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input ref={fileInputRef} type="file" className="text-sm" />
          <button
            onClick={handleUpload}
            disabled={pendingAction === "upload"}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-40"
          >
            {pendingAction === "upload" ? t("loading") : t("action_upload")}
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-400">PDF, JPEG or PNG, up to 5MB.</p>
      </section>

      {!documents ? (
        <p className="text-slate-500">{t("loading")}</p>
      ) : documents.length === 0 ? (
        <p className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500">
          No documents yet.
        </p>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => {
            const busy = pendingId === doc.id;
            return (
              <div key={doc.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-slate-900">{doc.doc_type.replaceAll("_", " ")}</p>
                    <p className="text-xs text-slate-500">{doc.original_filename}</p>
                  </div>
                  <span
                    className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${DOC_STATUS_CLASSES[doc.status]}`}
                  >
                    {t(DOC_STATUS_LABEL_KEY[doc.status])}
                  </span>
                </div>
                {doc.rejection_reason && (
                  <p className="mt-2 text-xs text-red-700">Rejected: {doc.rejection_reason}</p>
                )}
                {doc.used_by.length > 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    Used by: {doc.used_by.map((u) => u.life_event_title_en).join(", ")}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <VaultButton
                    label={t("action_submit_for_review")}
                    disabled={doc.status !== "uploaded"}
                    pending={busy && pendingAction === "review"}
                    onClick={() =>
                      runDocAction(doc.id, "review", () =>
                        citizenApi.submitDocumentForReview(citizenId, doc.id, token ?? undefined),
                      )
                    }
                  />
                  <VaultButton
                    label={t("action_verify")}
                    disabled={doc.status !== "under_review"}
                    pending={busy && pendingAction === "verify"}
                    onClick={() =>
                      runDocAction(doc.id, "verify", () =>
                        citizenApi.verifyDocument(citizenId, doc.id, token ?? undefined),
                      )
                    }
                  />
                  <VaultButton
                    label={t("action_reject")}
                    variant="secondary"
                    disabled={doc.status !== "under_review"}
                    pending={busy && pendingAction === "reject"}
                    onClick={() =>
                      runDocAction(doc.id, "reject", () =>
                        citizenApi.rejectDocument(
                          citizenId,
                          doc.id,
                          "Document illegible — please re-upload",
                          token ?? undefined,
                        ),
                      )
                    }
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}

function VaultButton({
  label,
  onClick,
  disabled,
  pending,
  variant = "primary",
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  pending?: boolean;
  variant?: "primary" | "secondary";
}) {
  const base =
    "rounded-lg px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40";
  const styles =
    variant === "primary"
      ? "bg-slate-900 text-white hover:bg-slate-700"
      : "border border-slate-300 text-slate-700 hover:bg-slate-50";
  return (
    <button className={`${base} ${styles}`} disabled={disabled || pending} onClick={onClick}>
      {pending ? "…" : label}
    </button>
  );
}
