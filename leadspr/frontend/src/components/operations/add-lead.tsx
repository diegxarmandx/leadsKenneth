"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ChevronDown, Plus, ShieldCheck } from "lucide-react";
import { Notice, Spinner } from "@/components/ui";
import { getMunicipalities } from "@/services/marketplace";
import { addLead } from "@/services/operations";
import { errorMessage } from "@/lib/api";
import type { LeadEntryInput } from "@/types/api";

type FieldErrors = Partial<Record<keyof LeadEntryInput, string>>;

export function AddLead({
  today,
  disabled,
  onBusyChange,
  onSaved,
}: {
  today: string;
  disabled: boolean;
  onBusyChange: (busy: boolean) => void;
  onSaved: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [places, setPlaces] = useState<string[]>([]);
  const [placesLoading, setPlacesLoading] = useState(false);
  const [placesError, setPlacesError] = useState("");
  const [retry, setRetry] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [feedback, setFeedback] = useState<{
    message: string;
    tone: "success" | "info";
  } | null>(null);
  const pending = useRef(false);
  const requestId = useRef<string | null>(null);
  const toggle = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void getMunicipalities(controller.signal, "all")
      .then(({ municipalities }) => {
        if (controller.signal.aborted) return;
        setPlaces(municipalities);
        setPlacesLoading(false);
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        setPlacesError(errorMessage(failure));
        setPlacesLoading(false);
      });
    return () => controller.abort();
  }, [open, retry]);

  function close() {
    setOpen(false);
    setErrors({});
    setError("");
    requestId.current = null;
    toggle.current?.focus();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current || disabled || placesLoading || placesError) return;
    const values = new FormData(event.currentTarget);
    const value = (key: string) => String(values.get(key) ?? "").trim();
    const data: LeadEntryInput = {
      first_name: value("first_name"),
      last_name: value("last_name") || null,
      phone: value("phone"),
      email: value("email") || null,
      municipality: value("municipality"),
      lead_date: value("lead_date"),
    };
    const invalid: FieldErrors = {};
    if (!data.first_name || data.first_name.length > 100)
      invalid.first_name = "Ingresa el nombre (máximo 100 caracteres).";
    if (data.last_name && data.last_name.length > 100)
      invalid.last_name = "Usa un máximo de 100 caracteres.";
    const digits = data.phone.replace(/\D/g, "").length;
    if (
      !/^\+?[0-9() .-]+$/.test(data.phone) ||
      digits < 7 ||
      digits > 15 ||
      data.phone.length > 30
    )
      invalid.phone = "Ingresa un teléfono válido de 7 a 15 dígitos.";
    if (
      data.email &&
      (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email) ||
        data.email.length > 254)
    )
      invalid.email = "Ingresa un correo electrónico válido.";
    if (!places.includes(data.municipality))
      invalid.municipality = "Selecciona un municipio de Puerto Rico.";
    const date = new Date(`${data.lead_date}T12:00:00Z`);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(data.lead_date) ||
      Number.isNaN(date.getTime()) ||
      date.toISOString().slice(0, 10) !== data.lead_date
    )
      invalid.lead_date = "Selecciona una fecha válida.";
    setErrors(invalid);
    if (Object.keys(invalid).length) {
      const first = event.currentTarget.elements.namedItem(
        Object.keys(invalid)[0],
      );
      if (first instanceof HTMLElement) first.focus();
      return;
    }
    pending.current = true;
    setSaving(true);
    onBusyChange(true);
    setError("");
    setFeedback(null);
    requestId.current ??= crypto.randomUUID();
    try {
      const result = await addLead(data, requestId.current);
      close();
      setFeedback(
        result.status === "synced"
          ? {
              tone: "success",
              message: `Lead añadido y sincronizado correctamente.${result.available ? " El lead ya está disponible en el inventario." : " Su disponibilidad seguirá las reglas actuales de fecha y precio."}`,
            }
          : {
              tone: "info",
              message:
                "El lead fue añadido a Google Sheets, pero no se pudo completar la sincronización automática. Presiona “Sincronizar Ahora” para intentar nuevamente. No necesitas añadirlo otra vez.",
            },
      );
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      pending.current = false;
      setSaving(false);
      onBusyChange(false);
    }
  }

  return (
    <div className="lead-entry">
      <div className="lead-entry-toolbar">
        <button
          ref={toggle}
          type="button"
          className="button button-gold"
          disabled={disabled || saving}
          aria-expanded={open}
          aria-controls="new-lead-form"
          onClick={() => {
            if (open) {
              close();
              return;
            }
            setPlacesLoading(true);
            setPlacesError("");
            setFeedback(null);
            setOpen(true);
          }}
        >
          <Plus size={17} aria-hidden="true" /> Añadir Lead
        </button>
      </div>
      {feedback && <Notice tone={feedback.tone}>{feedback.message}</Notice>}
      {open && (
        <section
          className="panel lead-entry-panel"
          aria-labelledby="new-lead-title"
        >
          <div className="lead-entry-heading">
            <div>
              <h3 id="new-lead-title">Nuevo Lead</h3>
              <p>Añade un prospecto y actualiza el inventario de tu agencia.</p>
            </div>
            <span className="lead-entry-insurance">
              <ShieldCheck size={17} aria-hidden="true" /> Seguro de Vida
            </span>
          </div>
          {placesError && (
            <Notice
              action={
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    setPlacesLoading(true);
                    setPlacesError("");
                    setRetry((current) => current + 1);
                  }}
                >
                  Cargar municipios nuevamente
                </button>
              }
            >
              {placesError}
            </Notice>
          )}
          <form
            id="new-lead-form"
            onSubmit={submit}
            noValidate
            aria-busy={saving}
          >
            <div className="lead-entry-fields">
              {(
                [
                  ["first_name", "Nombre", "text", "Ej. Ana", true],
                  ["last_name", "Apellido", "text", "Ej. Rivera", false],
                  ["phone", "Teléfono", "tel", "(787) 555-0100", true],
                  [
                    "email",
                    "Correo Electrónico",
                    "email",
                    "nombre@ejemplo.com",
                    false,
                  ],
                ] as const
              ).map(([name, label, type, placeholder, required]) => (
                <div className="field" key={name}>
                  <label htmlFor={`lead-${name}`}>
                    {label}
                    {!required && <span className="optional"> (opcional)</span>}
                  </label>
                  <input
                    id={`lead-${name}`}
                    name={name}
                    type={type}
                    placeholder={placeholder}
                    required={required}
                    maxLength={
                      name === "phone" ? 30 : name === "email" ? 254 : 100
                    }
                    disabled={saving}
                    autoComplete="off"
                    autoFocus={name === "first_name"}
                    aria-invalid={!!errors[name]}
                    aria-describedby={
                      errors[name] ? `lead-${name}-error` : undefined
                    }
                  />
                  {errors[name] && (
                    <p className="field-error" id={`lead-${name}-error`}>
                      {errors[name]}
                    </p>
                  )}
                </div>
              ))}
              <div className="field select-field">
                <label htmlFor="lead-municipality">Municipio</label>
                <div className="select-wrap">
                  <select
                    id="lead-municipality"
                    name="municipality"
                    defaultValue=""
                    required
                    disabled={saving || placesLoading || !!placesError}
                    aria-invalid={!!errors.municipality}
                    aria-describedby={
                      errors.municipality
                        ? "lead-municipality-error"
                        : undefined
                    }
                  >
                    <option value="">
                      {placesLoading
                        ? "Cargando municipios…"
                        : "Selecciona un municipio"}
                    </option>
                    {places.map((place) => (
                      <option key={place}>{place}</option>
                    ))}
                  </select>
                  <ChevronDown size={16} aria-hidden="true" />
                </div>
                {errors.municipality && (
                  <p className="field-error" id="lead-municipality-error">
                    {errors.municipality}
                  </p>
                )}
              </div>
              <div className="field">
                <label htmlFor="lead-date">Fecha del Lead</label>
                <input
                  id="lead-date"
                  name="lead_date"
                  type="date"
                  defaultValue={today}
                  required
                  disabled={saving}
                  aria-invalid={!!errors.lead_date}
                  aria-describedby={
                    errors.lead_date ? "lead-date-error" : "lead-date-help"
                  }
                />
                {errors.lead_date ? (
                  <p className="field-error" id="lead-date-error">
                    {errors.lead_date}
                  </p>
                ) : (
                  <p className="field-help" id="lead-date-help">
                    La antigüedad se calcula a partir de esta fecha.
                  </p>
                )}
              </div>
            </div>
            {error && <Notice>{error}</Notice>}
            <div className="lead-entry-actions">
              <button
                type="submit"
                className="button button-gold"
                disabled={saving || disabled || placesLoading || !!placesError}
              >
                {saving && <Spinner label="Añadiendo lead" />}
                {saving ? "Añadiendo lead..." : "Guardar Lead"}
              </button>
              <button
                type="button"
                className="button button-text"
                disabled={saving}
                onClick={close}
              >
                Cancelar
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
}
