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
import { getPurchase, refreshPurchase } from "@/services/marketplace";
import { ApiError, errorMessage } from "@/lib/api";
import { money } from "@/lib/format";
import type { PublicPurchase } from "@/types/api";

export function OrderStatus({ publicId }: { publicId?: string }) {
  const [order, setOrder] = useState<PublicPurchase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [pollingStopped, setPollingStopped] = useState(false);

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
      let result = await getPurchase(id, controller.signal);
      if (controller.signal.aborted) return;
      setOrder(result);
      const needsRefresh = (purchase: PublicPurchase) =>
        purchase.status === "PENDING" ||
        purchase.status === "PAID" ||
        (purchase.status === "FULFILLED" && !purchase.email_sent_at);
      if (needsRefresh(result)) {
        try {
          result = await refreshPurchase(id, controller.signal);
        } catch (failure) {
          if (controller.signal.aborted) throw failure;
          if (
            failure instanceof ApiError &&
            ["email_delivery_pending", "email_delivery_blocked"].includes(
              failure.code,
            )
          ) {
            // Allocation may have committed before email failed. Show the saved
            // order state while keeping the delivery error visible.
            const saved = await getPurchase(id, controller.signal);
            if (!controller.signal.aborted) setOrder(saved);
          }
          throw failure;
        }
        if (controller.signal.aborted) return;
        setOrder(result);
      }
      setError("");
      setLoading(false);
      const waiting = needsRefresh(result);
      if (waiting && ++attempts < 12) {
        timer = setTimeout(runPoll, Math.min(attempts * 2000, 10_000));
      } else {
        setPollingStopped(waiting);
      }
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
          <p className="eyebrow">FSG Seguros</p>
          <h1>{title}</h1>
          <p>
            {fulfilled
              ? "Tus leads ya están asignados. Gracias por confiar en FSG Seguros."
              : order?.status === "FULFILLMENT_FAILED"
                ? "Registramos tu pago de prueba, pero la cantidad completa ya no estaba disponible al precio seleccionado. No se asignaron leads parcialmente. La orden está marcada en Administración para revisión."
                : failed
                  ? "No se asignaron leads a esta orden. Puedes volver al marketplace cuando quieras."
                  : "Confirmar el pago y asignar los leads puede tomar un momento. Esta página se actualizará según avance tu orden."}
          </p>
          {error && <Notice>{error}</Notice>}
          {pollingStopped && !error && (
            <Notice tone="info">
              Tu orden todavía está en proceso. Pausamos las consultas
              automáticas. Puedes actualizar el estado en unos minutos; no
              vuelvas a pagar esta orden.
            </Notice>
          )}
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
                setPollingStopped(false);
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
