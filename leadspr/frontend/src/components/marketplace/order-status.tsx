"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Mail,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import { DemoBadge, Notice, Spinner } from "@/components/ui";
import { getPurchase } from "@/services/marketplace";
import { errorMessage } from "@/lib/api";
import { money } from "@/lib/format";
import type { PublicPurchase } from "@/types/api";

export function OrderStatus({ publicId }: { publicId?: string }) {
  const [order, setOrder] = useState<PublicPurchase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;
    let id = publicId;
    if (!id) {
      try {
        id = sessionStorage.getItem("borinquen-last-order") || undefined;
      } catch {
        /* Storage can be disabled. */
      }
    }
    async function poll() {
      if (controller.signal.aborted) return;
      if (!id || !/^ORD-[A-Z0-9-]{6,40}$/.test(id)) {
        setError(
          "No pudimos identificar esta orden. Revisa el enlace en tu correo o visita Administración.",
        );
        setLoading(false);
        return;
      }
      const result = await getPurchase(id, controller.signal);
      if (controller.signal.aborted) return;
      setOrder(result);
      setError("");
      setLoading(false);
      const waiting =
        result.status === "PENDING" ||
        result.status === "PAID" ||
        (result.status === "FULFILLED" && !result.email_sent_at);
      if (waiting && ++attempts < 60) timer = setTimeout(runPoll, 2000);
    }
    function runPoll() {
      // Timers do not consume returned promises; handle every poll explicitly.
      void poll().catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        setError(errorMessage(failure));
        setLoading(false);
      });
    }
    runPoll();
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [publicId, refresh]);

  const fulfilled = order?.status === "FULFILLED";
  const failed =
    order?.status === "FAILED" || order?.status === "FULFILLMENT_FAILED";
  const title = fulfilled
    ? "Tu orden está completada."
    : order?.status === "FULFILLMENT_FAILED"
      ? "Tu orden requiere atención."
      : failed
        ? "El pago no se completó."
        : "Estamos confirmando tu orden.";
  return (
    <div className="workspace">
      <div className="container order-status-container">
        <DemoBadge />
        <section className="panel order-status-panel">
          <span
            className={`order-result-icon ${failed ? "result-warning" : ""}`}
          >
            {loading ? (
              <Spinner label="Cargando la orden" />
            ) : fulfilled ? (
              <CheckCircle2 size={35} aria-hidden="true" />
            ) : failed ? (
              <TriangleAlert size={32} aria-hidden="true" />
            ) : (
              <Clock3 size={33} aria-hidden="true" />
            )}
          </span>
          <p className="eyebrow">Borinquen Life &amp; Protection</p>
          <h1>{title}</h1>
          <p>
            {fulfilled
              ? "Tus leads ya están asignados. Gracias por confiar en Borinquen Life & Protection."
              : order?.status === "FULFILLMENT_FAILED"
                ? "Registramos tu pago de prueba, pero la cantidad completa ya no estaba disponible al precio seleccionado. No se asignaron leads parcialmente. La orden está marcada en Administración para revisión."
                : failed
                  ? "No se asignaron leads a esta orden. Puedes volver al marketplace cuando quieras."
                  : "Confirmar el pago y asignar los leads puede tomar un momento. Esta página se actualizará según avance tu orden."}
          </p>
          {error && <Notice>{error}</Notice>}
          {order && (
            <dl className="order-result-details">
              <div>
                <dt>Orden</dt>
                <dd>{order.public_id}</dd>
              </div>
              <div>
                <dt>Municipio</dt>
                <dd>{order.municipality || "Todo Puerto Rico"}</dd>
              </div>
              <div>
                <dt>Leads</dt>
                <dd>{order.requested_quantity}</dd>
              </div>
              <div>
                <dt>Precio por Lead</dt>
                <dd>{money(order.price_per_lead_cents)}</dd>
              </div>
              <div>
                <dt>Total de la orden</dt>
                <dd>{money(order.total_amount_cents)}</dd>
              </div>
            </dl>
          )}
          {fulfilled && (
            <div className="email-confirmation">
              <Mail size={20} aria-hidden="true" />
              <span>
                {order?.email_sent_at
                  ? "Enviamos el correo con tus leads. Revisa tu bandeja de entrada."
                  : "Tus leads ya están asignados. El envío del correo está pendiente de confirmación."}
              </span>
            </div>
          )}
          <div className="result-actions">
            <Link href="/leads" className="button button-primary">
              Volver al Marketplace <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <button
              className="button button-text"
              disabled={loading}
              onClick={() => {
                setLoading(true);
                setRefresh((value) => value + 1);
              }}
            >
              <RefreshCw size={15} aria-hidden="true" />
              Actualizar estado
            </button>
          </div>
          <Link href="/admin" className="text-button result-operations">
            Ver Administración <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </section>
      </div>
    </div>
  );
}
