import { Minus, Plus } from "lucide-react";
import { number } from "@/lib/format";

export function QuantitySelector({
  value,
  max,
  disabled,
  onChange,
}: {
  value: string;
  max: number;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const quantity = Number(value);
  const valid =
    value !== "" &&
    Number.isInteger(quantity) &&
    quantity >= 1 &&
    quantity <= max;
  return (
    <div className="quantity-row">
      <div>
        <label htmlFor="quantity" className="field-title">
          ¿Cuántos leads necesitas?
        </label>
        <p className="field-help">
          {max > 0
            ? `Escoge entre 1 y ${number(max)} leads disponibles.`
            : "Escoge un tipo de lead disponible para continuar."}
        </p>
      </div>
      <div className="quantity-controls">
        <div className="quantity-input">
          <button
            type="button"
            aria-label="Reducir cantidad"
            disabled={disabled || quantity <= 1}
            onClick={() => onChange(String(Math.max(1, quantity - 1)))}
          >
            <Minus size={16} aria-hidden="true" />
          </button>
          <input
            id="quantity"
            type="number"
            inputMode="numeric"
            value={value}
            min={1}
            max={max || 1}
            step={1}
            required
            disabled={disabled}
            aria-invalid={!disabled && !valid}
            aria-describedby={
              !disabled && !valid ? "quantity-error" : undefined
            }
            onChange={(event) => {
              if (/^\d*$/.test(event.target.value))
                onChange(event.target.value);
            }}
          />
          <button
            type="button"
            aria-label="Aumentar cantidad"
            disabled={disabled || quantity >= max}
            onClick={() =>
              onChange(String(Math.min(max, Math.max(1, quantity + 1))))
            }
          >
            <Plus size={16} aria-hidden="true" />
          </button>
        </div>
        {!disabled && !valid && (
          <p id="quantity-error" className="field-error">
            Ingresa un número entero del 1 al {number(max)}.
          </p>
        )}
      </div>
    </div>
  );
}
