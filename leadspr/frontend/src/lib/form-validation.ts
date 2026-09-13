import type { FormEvent } from "react";

export function spanishValidation(event: FormEvent<HTMLFormElement>): void {
  const field = event.target;
  if (!(field instanceof HTMLInputElement)) return;
  field.setCustomValidity(
    field.validity.valueMissing
      ? "Completa este campo para continuar."
      : field.validity.typeMismatch
        ? "Ingresa un correo electrónico válido."
        : "Revisa el valor de este campo antes de continuar.",
  );
}

export function clearValidation(event: FormEvent<HTMLFormElement>): void {
  if (event.target instanceof HTMLInputElement)
    event.target.setCustomValidity("");
}
