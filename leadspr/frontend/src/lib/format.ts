import type { InventoryTier } from "@/types/api";

const currency = new Intl.NumberFormat("es-PR", {
  style: "currency",
  currency: "USD",
});
const wholeCurrency = new Intl.NumberFormat("es-PR", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const integer = new Intl.NumberFormat("es-PR");
export const money = (cents: number, compact = false) =>
  (compact && cents % 100 === 0 ? wholeCurrency : currency).format(cents / 100);
export const number = (value: number) => integer.format(value);
export const dateTime = (value: string) =>
  new Intl.DateTimeFormat("es-PR", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Puerto_Rico",
  }).format(new Date(value));
export const ageRange = (min: number, max: number | null) =>
  max === null ? `${min}+ días` : `${min}–${max} días`;

export function tierPresentation(tier: InventoryTier) {
  const range = tier.age_ranges[0];
  const standard =
    tier.age_ranges.length === 1
      ? (
          {
            0: [
              "Leads Nuevos",
              "Los prospectos más recientes disponibles actualmente.",
              "fresh",
            ],
            8: [
              "Leads Recientes",
              "Prospectos recientes con buen potencial para seguimiento.",
              "recent",
            ],
            31: [
              "Leads de Seguimiento",
              "Prospectos con más tiempo disponibles a un menor costo de adquisición.",
              "established",
            ],
            61: [
              "Leads Antiguos",
              "Prospectos económicos para esfuerzos continuos de seguimiento.",
              "aged",
            ],
          } as const
        )[range?.min_age_days as 0 | 8 | 31 | 61]
      : undefined;
  return {
    name: standard?.[0] ?? "Leads de Seguro de Vida",
    description:
      standard?.[1] ??
      "Prospectos dentro del rango de antigüedad seleccionado.",
    key: standard?.[2] ?? "custom",
    age: tier.age_ranges
      .map((item) => ageRange(item.min_age_days, item.max_age_days))
      .join(" / "),
  };
}
