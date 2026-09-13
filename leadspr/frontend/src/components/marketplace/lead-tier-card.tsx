import { Check, Clock3, Sparkles, Sprout, History } from "lucide-react";
import { money, number, tierPresentation } from "@/lib/format";
import type { InventoryTier } from "@/types/api";

export function LeadTierCard({
  tier,
  selected,
  disabled,
  onSelect,
}: {
  tier: InventoryTier;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  const info = tierPresentation(tier);
  const Icon =
    info.key === "fresh"
      ? Sparkles
      : info.key === "recent"
        ? Clock3
        : info.key === "established"
          ? Sprout
          : History;
  const available = tier.available_quantity > 0;
  return (
    <label
      className={`tier-card ${selected ? "tier-selected" : ""} ${!available ? "tier-unavailable" : ""}`}
    >
      <input
        className="sr-only"
        type="radio"
        name="lead-tier"
        value={tier.price_cents}
        checked={selected}
        disabled={disabled || !available}
        onChange={onSelect}
      />
      <div className="tier-card-top">
        <span className={`tier-icon tier-${info.key}`}>
          <Icon size={19} aria-hidden="true" />
        </span>
        <span className="tier-radio" aria-hidden="true">
          {selected && <Check size={12} strokeWidth={3} />}
        </span>
      </div>
      <div className="tier-title-row">
        <h3>{info.name}</h3>
        <span className="tier-age">{info.age}</span>
      </div>
      <div className="tier-price">
        {money(tier.price_cents, true)}
        <span> / lead</span>
      </div>
      <p>{info.description}</p>
      <div className={`availability ${!available ? "empty" : ""}`}>
        <span aria-hidden="true" />
        {available
          ? `${number(tier.available_quantity)} disponibles`
          : "No disponible por el momento"}
      </div>
    </label>
  );
}
