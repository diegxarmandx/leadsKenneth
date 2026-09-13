"use client";

import { useRef, useState, type FormEvent } from "react";
import { Clock3, Info, Pencil } from "lucide-react";
import { ageRange, money } from "@/lib/format";
import { parsePriceCents, priceInputValue } from "@/lib/price-input";
import { updatePrice } from "@/services/operations";
import { errorMessage } from "@/lib/api";
import { Notice, Spinner } from "@/components/ui";
import type { PricingRule } from "@/types/api";

export function PricingRules({
  rules,
  disabled,
  onSaved,
}: {
  rules: PricingRule[];
  disabled: boolean;
  onSaved: (rule: PricingRule) => Promise<void>;
}) {
  const [editing, setEditing] = useState<number | null>(null);
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const pending = useRef(false);

  async function save(event: FormEvent<HTMLFormElement>, rule: PricingRule) {
    event.preventDefault();
    if (pending.current || disabled) return;
    const cents = parsePriceCents(value);
    if (cents === null) {
      setError(
        "Ingresa un precio mayor de cero con un máximo de dos decimales.",
      );
      return;
    }
    pending.current = true;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updatePrice(rule.id, cents);
      setEditing(null);
      setSuccess(
        `El precio de ${ageRange(updated.min_age_days, updated.max_age_days)} se actualizó correctamente a ${money(updated.price_cents)}.`,
      );
      await onSaved(updated);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      pending.current = false;
      setSaving(false);
    }
  }

  return (
    <section className="panel pricing-panel">
      <div className="panel-heading">
        <div>
          <h2>Reglas de Precios</h2>
          <p>
            Actualiza el precio por lead. La antigüedad y la exclusividad se
            mantienen.
          </p>
        </div>
        <span className="subtle-badge">
          <Clock3 size={15} aria-hidden="true" />
          Antigüedad automática
        </span>
      </div>
      <div className="pricing-content">
        <div className="pricing-editor">
          <div
            className="table-scroll"
            role="region"
            aria-label="Reglas de precios editables"
            tabIndex={0}
          >
            <table className="data-table pricing-table">
              <thead>
                <tr>
                  <th scope="col">Edad del Lead</th>
                  <th scope="col">Precio</th>
                  <th scope="col">Exclusividad</th>
                  <th scope="col">Acción</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr
                    key={rule.id}
                    className={
                      editing === rule.id ? "pricing-row-editing" : undefined
                    }
                  >
                    <th scope="row">
                      {ageRange(rule.min_age_days, rule.max_age_days)}
                    </th>
                    <td>
                      {editing === rule.id ? (
                        <div className="price-input-wrap">
                          <span aria-hidden="true">$</span>
                          <input
                            form={`price-form-${rule.id}`}
                            aria-label={`Precio para ${ageRange(rule.min_age_days, rule.max_age_days)}`}
                            aria-invalid={!!error}
                            aria-describedby={
                              error ? "price-feedback" : "pricing-help"
                            }
                            type="text"
                            inputMode="decimal"
                            value={value}
                            maxLength={16}
                            autoFocus
                            disabled={saving}
                            onChange={(event) => {
                              setValue(event.target.value);
                              setError("");
                            }}
                          />
                        </div>
                      ) : (
                        <>
                          <strong>{money(rule.price_cents)}</strong>
                          <span className="per-lead"> / lead</span>
                        </>
                      )}
                    </td>
                    <td>
                      {rule.exclusion_days}{" "}
                      {rule.exclusion_days === 1 ? "día" : "días"}
                    </td>
                    <td>
                      {editing === rule.id ? (
                        <form
                          id={`price-form-${rule.id}`}
                          className="pricing-actions"
                          onSubmit={(event) => save(event, rule)}
                          noValidate
                        >
                          <button
                            type="submit"
                            className="button button-primary button-small"
                            disabled={saving || disabled}
                          >
                            {saving ? (
                              <>
                                <Spinner label="Guardando precio" />
                                Guardando...
                              </>
                            ) : (
                              "Guardar"
                            )}
                          </button>
                          <button
                            type="button"
                            className="text-button"
                            disabled={saving}
                            onClick={() => {
                              setEditing(null);
                              setError("");
                            }}
                          >
                            Cancelar
                          </button>
                        </form>
                      ) : (
                        <button
                          type="button"
                          className="text-button edit-price"
                          aria-label={`Editar precio de ${ageRange(rule.min_age_days, rule.max_age_days)}`}
                          disabled={saving || disabled || editing !== null}
                          onClick={() => {
                            setEditing(rule.id);
                            setValue(priceInputValue(rule.price_cents));
                            setError("");
                            setSuccess("");
                          }}
                        >
                          <Pencil size={14} aria-hidden="true" />
                          Editar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!rules.length && (
            <p className="empty-caption">No hay reglas de precios activas.</p>
          )}
          <div className="pricing-feedback" id="price-feedback">
            {error && <Notice>{error}</Notice>}
            {success && <Notice tone="success">{success}</Notice>}
          </div>
          <p className="pricing-help" id="pricing-help">
            Usa un precio mayor de cero, con un máximo de dos decimales. Cada
            rango debe tener un precio distinto.
          </p>
        </div>
        <aside className="pricing-explainer">
          <span className="mini-icon">
            <Info size={20} aria-hidden="true" />
          </span>
          <h3>El precio cambia con la antigüedad.</h3>
          <p>
            Los prospectos pasan al siguiente rango automáticamente. Después de
            una compra, vuelven a estar disponibles al terminar su período de
            exclusividad.
          </p>
          <p>
            Los cambios aplican a las próximas compras. Las órdenes completadas
            conservan su precio original.
          </p>
          <p>
            Termina los pagos pendientes de este tipo de lead antes de cambiar
            su precio.
          </p>
        </aside>
      </div>
    </section>
  );
}
