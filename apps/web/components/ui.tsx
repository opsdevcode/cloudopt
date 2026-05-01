import type { ReactNode } from "react";

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-ops-lg border border-border bg-bg shadow-card p-6 transition-shadow hover:shadow-opsmd ${className}`}
    >
      {title ? <h2 className="text-lg font-semibold tracking-tight text-text m-0 mb-4">{title}</h2> : null}
      {children}
    </section>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  let cls =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-bg-muted text-text-secondary";
  if (s === "critical" || s === "high") cls = "bg-error/10 text-error";
  else if (s === "medium") cls = "bg-warning/15 text-warning";
  else if (s === "low" || s === "informational") cls = "bg-info/10 text-info";
  else if (s === "passed" || s === "success") cls = "bg-success/10 text-success";
  return <span className={cls}>{severity}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  let cls = "bg-bg-muted text-text-secondary";
  if (s === "completed") cls = "bg-success/10 text-success";
  else if (s === "failed") cls = "bg-error/10 text-error";
  else if (s === "running") cls = "bg-info/10 text-info";
  else if (s === "pending") cls = "bg-warning/10 text-warning";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>{status}</span>
  );
}

export function PrimaryButton({
  children,
  type = "button",
  disabled,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded-ops-md px-6 py-2.5 text-sm font-semibold text-white bg-primary hover:bg-primary-hover shadow-md disabled:opacity-50 transition-colors"
      {...rest}
    >
      {children}
    </button>
  );
}

export function GhostButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className="inline-flex items-center justify-center rounded-ops-md border border-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-bg-muted transition-colors"
      {...props}
    />
  );
}
