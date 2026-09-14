"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ChevronDown,
  ChevronRight,
  MapPin,
  RefreshCw,
  Shuffle,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { DemoBadge, Notice, SectionTitle } from "@/components/ui";
import { LeadTierCard } from "@/components/marketplace/lead-tier-card";
import { QuantitySelector } from "@/components/marketplace/quantity-selector";
import { OrderSummary } from "@/components/marketplace/order-summary";
import {
  createCheckout,
  getCheckoutConfig,
  getInventory,
  getMunicipalities,
} from "@/services/marketplace";
import { ApiError, errorMessage } from "@/lib/api";
import { number } from "@/lib/format";
import { spanishValidation, clearValidation } from "@/lib/form-validation";
import type { CheckoutConfig, InventorySummary } from "@/types/api";

export function Marketplace() {
  const [municipality, setMunicipality] = useState("");
  const [municipalities, setMunicipalities] = useState<string[]>([]);
  const [inventory, setInventory] = useState<InventorySummary | null>(null);
  const [config, setConfig] = useState<CheckoutConfig | null>(null);
  const [price, setPrice] = useState<number | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checkoutError, setCheckoutError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const submitting = useRef(false);
  const selectedPrice = useRef<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      const [data, places, payment] = await Promise.all([
        getInventory(municipality || undefined, controller.signal),
        getMunicipalities(controller.signal),
        getCheckoutConfig(controller.signal),
      ]);
      if (controller.signal.aborted) return;
      const previous = data.tiers.find(
        (tier) =>
          tier.price_cents === selectedPrice.current &&
          tier.available_quantity > 0,
      );
      const preferred = data.tiers.find(
        (tier) =>
          tier.age_ranges.some((range) => range.min_age_days === 8) &&
          tier.available_quantity > 0,
      );
      const chosen =
        previous ??
        preferred ??
        data.tiers.find((tier) => tier.available_quantity > 0);
      selectedPrice.current = chosen?.price_cents ?? null;
      setPrice(selectedPrice.current);
      setQuantity((current) =>
        chosen
          ? String(
              Math.min(
                Math.max(1, Number(current) || 1),
                chosen.available_quantity,
              ),
            )
          : "1",
      );
      setInventory(data);
      setMunicipalities(places.municipalities);
      setConfig(payment);
      setError("");
      setLoading(false);
    }
    // Own the entire async chain, including processing the fetched data.
    void load().catch((failure: unknown) => {
      if (controller.signal.aborted) return;
      setError(errorMessage(failure));
      setLoading(false);
    });
    return () => controller.abort();
  }, [municipality, refresh]);

  function reload() {
    setLoading(true);
    setError("");
    setRefresh((current) => current + 1);
  }
  function changeLocation(value: string) {
    setMunicipality(value);
    setLoading(true);
    setError("");
    setCheckoutError("");
  }
  const tier =
    !loading && !error
      ? inventory?.tiers.find(
          (item) => item.price_cents === price && item.available_quantity > 0,
        )
      : undefined;
  const validQuantity =
    !!tier &&
    quantity !== "" &&
    Number.isInteger(Number(quantity)) &&
    Number(quantity) >= 1 &&
    Number(quantity) <= tier.available_quantity;
  const testMode = config?.payment_mode === "test";
  const canCheckout = !loading && !error && validQuantity && testMode;
  const available =
    inventory?.tiers.reduce(
      (total, item) => total + item.available_quantity,
      0,
    ) ?? 0;

  async function checkout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || !canCheckout || !tier) return;
    submitting.current = true;
    setBusy(true);
    setCheckoutError("");
    const data = new FormData(event.currentTarget);
    try {
      const result = await createCheckout({
        buyer_name: String(data.get("buyer_name") ?? "").trim(),
        buyer_email: String(data.get("buyer_email") ?? "").trim(),
        buyer_phone: String(data.get("buyer_phone") ?? "").trim() || undefined,
        insurance_type: "Life Insurance",
        municipality: municipality || undefined,
        quantity: Number(quantity),
        price_per_lead_cents: tier.price_cents,
      });
      try {
        sessionStorage.setItem("borinquen-last-order", result.public_id);
      } catch {
        /* Query parameter remains the primary order reference. */
      }
      window.location.assign(result.checkout_url);
    } catch (failure) {
      setCheckoutError(errorMessage(failure));
      setBusy(false);
      submitting.current = false;
      if (
        failure instanceof ApiError &&
        (failure.status === 409 || failure.code === "pricing_rule_not_found")
      )
        reload();
    }
  }

  return (
    <div className="workspace marketplace-page">
      <div className="container">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Para profesionales de seguros</p>
            <h1>Marketplace de Leads de Seguro de Vida</h1>
            <p>
              Selecciona un municipio, escoge la antigüedad del lead que mejor
              se ajuste a tu estrategia y compra la cantidad que necesites.
            </p>
          </div>
          <DemoBadge />
        </div>
        <ol className="steps" aria-label="Pasos para comprar">
          {[
            "Escoge la ubicación",
            "Escoge el tipo de lead",
            "Selecciona la cantidad",
            "Paga",
          ].map((label, index) => (
            <li key={label}>
              <span className={`step-number ${index < 3 ? "step-ready" : ""}`}>
                {index + 1}
              </span>
              <span>{label}</span>
              {index < 3 && <ChevronRight size={15} aria-hidden="true" />}
            </li>
          ))}
        </ol>
        <form
          onSubmit={checkout}
          onInvalid={spanishValidation}
          onInput={clearValidation}
          className="marketplace-grid"
        >
          <div className="configuration">
            <section className="panel location-panel">
              <SectionTitle number="01" title="Escoge la ubicación">
                <MapPin size={18} aria-hidden="true" />
              </SectionTitle>
              <div className="location-row">
                <div className="select-field">
                  <label htmlFor="municipality">Municipio</label>
                  <div className="select-wrap">
                    <MapPin size={17} aria-hidden="true" />
                    <select
                      id="municipality"
                      value={municipality}
                      onChange={(event) => changeLocation(event.target.value)}
                      disabled={busy}
                    >
                      <option value="">Todo Puerto Rico</option>
                      {[
                        ...new Set([
                          ...municipalities,
                          ...(municipality ? [municipality] : []),
                        ]),
                      ]
                        .sort((a, b) => a.localeCompare(b))
                        .map((place) => (
                          <option key={place}>{place}</option>
                        ))}
                    </select>
                    <ChevronDown size={16} aria-hidden="true" />
                  </div>
                </div>
                <div className="location-caption">
                  <span className="mini-icon">
                    <MapPin size={18} aria-hidden="true" />
                  </span>
                  <p>
                    Alcance en toda la isla.
                    <br />
                    <strong>Conexiones locales.</strong>
                  </p>
                </div>
              </div>
            </section>
            <section className="tier-section" aria-busy={loading}>
              <SectionTitle number="02" title="Escoge el tipo de lead">
                <span className="section-caption">
                  Un tipo de lead por orden
                </span>
              </SectionTitle>
              {error ? (
                <Notice
                  action={
                    <button
                      type="button"
                      className="text-button"
                      onClick={reload}
                    >
                      <RefreshCw size={14} aria-hidden="true" />
                      Intenta nuevamente
                    </button>
                  }
                >
                  {error}
                </Notice>
              ) : loading ? (
                <div
                  className="tier-grid"
                  role="status"
                  aria-label="Cargando los tipos de leads disponibles"
                >
                  {[0, 1, 2, 3].map((i) => (
                    <div className="tier-card skeleton-card" key={i}>
                      <div className="skeleton skeleton-icon" />
                      <div className="skeleton skeleton-line" />
                      <div className="skeleton skeleton-price" />
                      <div className="skeleton skeleton-line" />
                    </div>
                  ))}
                </div>
              ) : inventory?.tiers.length ? (
                <>
                  <fieldset className="tier-grid">
                    <legend className="sr-only">Tipo de lead</legend>
                    {inventory.tiers.map((item) => (
                      <LeadTierCard
                        key={item.price_cents}
                        tier={item}
                        selected={item.price_cents === price}
                        disabled={busy}
                        onSelect={() => {
                          setPrice(item.price_cents);
                          selectedPrice.current = item.price_cents;
                          setQuantity((current) =>
                            String(
                              Math.min(
                                Math.max(1, Number(current) || 1),
                                item.available_quantity,
                              ),
                            ),
                          );
                          setCheckoutError("");
                        }}
                      />
                    ))}
                  </fieldset>
                  {available === 0 && (
                    <Notice tone="info">
                      No hay leads disponibles en este municipio por el momento.
                      Escoge otro municipio o vuelve después de la próxima
                      actualización de inventario.
                    </Notice>
                  )}
                </>
              ) : (
                <Notice tone="info">
                  Los tipos de leads aún no están disponibles. Intenta
                  nuevamente en unos minutos.
                </Notice>
              )}
            </section>
            <section className="panel">
              <SectionTitle number="03" title="Selecciona la cantidad" />
              <QuantitySelector
                value={quantity}
                max={tier?.available_quantity ?? 0}
                disabled={!tier || busy}
                onChange={setQuantity}
              />
            </section>
            <section className="panel delivery-panel">
              <SectionTitle title="¿Dónde quieres recibir tus leads?">
                <Mail size={18} aria-hidden="true" />
              </SectionTitle>
              <p className="section-description">
                No necesitas una cuenta. Recibirás tu orden y los leads
                asignados por correo electrónico.
              </p>
              <div className="buyer-fields">
                <div className="field">
                  <label htmlFor="buyer-name">
                    Nombre completo <span>*</span>
                  </label>
                  <input
                    id="buyer-name"
                    name="buyer_name"
                    autoComplete="name"
                    required
                    maxLength={200}
                    placeholder="Tu nombre completo"
                    disabled={busy}
                  />
                </div>
                <div className="field">
                  <label htmlFor="buyer-email">
                    Correo electrónico <span>*</span>
                  </label>
                  <input
                    id="buyer-email"
                    name="buyer_email"
                    type="email"
                    autoComplete="email"
                    required
                    maxLength={254}
                    placeholder="tu@agencia.com"
                    disabled={busy}
                  />
                </div>
                <div className="field">
                  <label htmlFor="buyer-phone">
                    Teléfono <span className="optional">(opcional)</span>
                  </label>
                  <input
                    id="buyer-phone"
                    name="buyer_phone"
                    type="tel"
                    autoComplete="tel"
                    maxLength={50}
                    placeholder="(787) 555-0123"
                    disabled={busy}
                  />
                </div>
              </div>
            </section>
            <div className="assignment-note">
              <Shuffle size={18} aria-hidden="true" />
              <p>
                Los leads se asignan aleatoriamente según el inventario
                disponible. No se pueden seleccionar leads individuales antes de
                la compra.
              </p>
            </div>
            {checkoutError && <Notice>{checkoutError}</Notice>}
          </div>
          <OrderSummary
            tier={tier}
            municipality={municipality}
            quantity={quantity}
            busy={busy}
            canCheckout={!!canCheckout}
            loading={loading}
            testMode={testMode}
          />
        </form>
        <div className="marketplace-bottom-note">
          <ShieldCheck size={16} aria-hidden="true" />
          <span>Leads de seguro de vida. Precios claros. Pago seguro.</span>
          {!loading && inventory && !error && (
            <span>
              {number(available)} leads disponibles en{" "}
              {municipality || "Puerto Rico"}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
