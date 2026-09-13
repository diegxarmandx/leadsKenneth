import type { PurchaseStatus } from "@/types/api";

const labels: Record<PurchaseStatus, string> = {
  FULFILLED: "Completada",
  PENDING: "Pendiente",
  PAID: "Asignando leads",
  FAILED: "Fallida",
  FULFILLMENT_FAILED: "Requiere atención",
};
export function StatusBadge({ status }: { status: PurchaseStatus }) {
  const tone =
    status === "FULFILLED"
      ? "success"
      : status === "FAILED" || status === "FULFILLMENT_FAILED"
        ? "danger"
        : "pending";
  return (
    <span className={`status-badge status-${tone}`}>
      <span aria-hidden="true" />
      {labels[status]}
    </span>
  );
}
