import { AlertCircle, CheckCircle2, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

export function DemoBadge() {
  return (
    <span className="demo-badge">
      <span aria-hidden="true" />
      MODO DEMO
    </span>
  );
}
export function Spinner({ label = "Cargando" }: { label?: string }) {
  return (
    <LoaderCircle className="spinner" size={18} role="img" aria-label={label} />
  );
}
export function Notice({
  children,
  tone = "error",
  action,
}: {
  children: ReactNode;
  tone?: "error" | "success" | "info";
  action?: ReactNode;
}) {
  const Icon = tone === "success" ? CheckCircle2 : AlertCircle;
  return (
    <div
      className={`notice notice-${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <Icon size={18} aria-hidden="true" />
      <div>
        {children}
        {action && <div className="notice-action">{action}</div>}
      </div>
    </div>
  );
}
export function SectionTitle({
  number,
  title,
  children,
}: {
  number?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="section-title">
      <h2>
        {number && <span className="section-number">{number}</span>}
        {title}
      </h2>
      {children}
    </div>
  );
}
