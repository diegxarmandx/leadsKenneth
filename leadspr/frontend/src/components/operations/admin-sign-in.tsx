"use client";

import { useRef, useState, type FormEvent } from "react";
import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import { Notice, Spinner } from "@/components/ui";
import { signIn } from "@/services/operations";
import { errorMessage } from "@/lib/api";
import { spanishValidation, clearValidation } from "@/lib/form-validation";

export function AdminSignIn({
  onAuthenticated,
}: {
  onAuthenticated: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    const passcode = String(
      new FormData(event.currentTarget).get("passcode") ?? "",
    );
    try {
      await signIn(passcode);
      onAuthenticated();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="admin-sign-in">
      <div className="sign-in-copy">
        <ShieldCheck size={42} strokeWidth={1.2} aria-hidden="true" />
        <p className="eyebrow">Tu agencia, de un vistazo</p>
        <h2>
          Detrás de cada conexión,
          <br />
          una visión clara.
        </h2>
        <p>
          Inventario, órdenes y tu próxima oportunidad.
          <br />
          Todo en un solo lugar.
        </p>
        <span className="sign-in-footnote">FSG Seguros</span>
      </div>
      <form
        onSubmit={submit}
        onInvalid={spanishValidation}
        onInput={clearValidation}
        className="sign-in-form"
      >
        <span className="mini-icon">
          <LockKeyhole size={22} aria-hidden="true" />
        </span>
        <h2>Acceso Administrativo</h2>
        <p>Ingresa tu contraseña de demostración para continuar.</p>
        <div className="field">
          <label htmlFor="passcode">Contraseña</label>
          <input
            id="passcode"
            name="passcode"
            type="password"
            autoComplete="current-password"
            required
            maxLength={256}
            placeholder="Ingresa tu contraseña"
            disabled={busy}
          />
        </div>
        {error && <Notice>{error}</Notice>}
        <button className="button button-primary" disabled={busy}>
          {busy ? <Spinner label="Iniciando sesión" /> : null}
          {busy ? "Entrando…" : "Entrar"}
          {!busy && <ArrowRight size={16} aria-hidden="true" />}
        </button>
        <p className="sign-in-hint">
          Acceso exclusivo para el equipo de demostración de la agencia.
        </p>
      </form>
    </div>
  );
}
