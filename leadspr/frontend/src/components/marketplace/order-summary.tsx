import { ArrowRight, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { money, tierPresentation } from "@/lib/format";
import { Spinner } from "@/components/ui";
import type { InventoryTier } from "@/types/api";

export function OrderSummary({
  tier,
  municipality,
  quantity,
  busy,
  canCheckout,
  loading,
  testMode,
}: {
  tier: InventoryTier | undefined;
  municipality: string;
  quantity: string;
  busy: boolean;
  canCheckout: boolean;
  loading: boolean;
  testMode: boolean;
}) {
  const info = tier ? tierPresentation(tier) : undefined;
  const count = Number(quantity);
  const valid =
    !!tier &&
    Number.isInteger(count) &&
    count > 0 &&
    count <= tier.available_quantity;
  return (
    <aside className="order-aside">
      <div className="order-summary">
        <div className="summary-heading">
          <span className="summary-icon">
            <ShieldCheck size={21} aria-hidden="true" />
          </span>
          <h2>Resumen de la Orden</h2>
        </div>
        <dl className="summary-details">
          <div>
            <dt>Municipio</dt>
            <dd>{municipality || "Todo Puerto Rico"}</dd>
          </div>
          <div>
            <dt>Tipo de Lead</dt>
            <dd>
              {loading ? "Cargando…" : (info?.name ?? "Escoge un tipo de lead")}
            </dd>
          </div>
          <div>
            <dt>Antigüedad</dt>
            <dd>{!loading && info ? info.age : "—"}</dd>
          </div>
          <div>
            <dt>Cantidad</dt>
            <dd>{!loading && valid ? count : "—"}</dd>
          </div>
          <div>
            <dt>Precio por Lead</dt>
            <dd>{!loading && tier ? money(tier.price_cents) : "—"}</dd>
          </div>
        </dl>
        <div className="summary-total" aria-live="polite" aria-atomic="true">
          <span>
            Total <small>USD</small>
          </span>
          <strong>
            {!loading && valid && tier ? money(tier.price_cents * count) : "—"}
          </strong>
        </div>
        <button
          className="button button-primary checkout-button"
          type="submit"
          disabled={!canCheckout || busy}
        >
          {busy ? (
            <>
              <Spinner label="Preparando el pago" />
              Abriendo el pago de prueba…
            </>
          ) : (
            <>
              Continuar al Pago Seguro{" "}
              <ArrowRight size={16} aria-hidden="true" />
            </>
          )}
        </button>
        <p className="stripe-note">
          <LockKeyhole size={12} aria-hidden="true" />
          Pago seguro procesado por <strong>Stripe.</strong>
        </p>
        <div className="summary-delivery">
          <Mail size={18} aria-hidden="true" />
          <div>
            <strong>Recibe tus leads por correo</strong>
            <p>
              Te enviaremos tus leads por correo cuando se confirmen el pago y
              la asignación.
            </p>
          </div>
        </div>
      </div>
      <div className="test-payment-note">
        <ShieldCheck size={17} aria-hidden="true" />
        <p>
          {testMode
            ? "Las transacciones utilizan el modo de prueba de Stripe y todos los datos de clientes son simulados."
            : "Esta demostración requiere el modo de prueba de Stripe. El pago estará disponible cuando se active."}
        </p>
      </div>
    </aside>
  );
}
