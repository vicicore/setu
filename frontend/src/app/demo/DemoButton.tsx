"use client";

export function DemoButton({
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
    "rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40";
  const styles =
    variant === "primary"
      ? "bg-slate-900 text-white hover:bg-slate-700"
      : "border border-slate-300 text-slate-700 hover:bg-slate-50";
  return (
    <button className={`${base} ${styles}`} disabled={disabled || pending} onClick={onClick}>
      {pending ? "Working…" : label}
    </button>
  );
}
