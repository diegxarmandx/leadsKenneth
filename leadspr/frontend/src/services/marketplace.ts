import { apiRequest } from "@/lib/api";
import type {
  CheckoutConfig,
  CheckoutRequest,
  CheckoutResponse,
  InventorySummary,
  PublicPurchase,
} from "@/types/api";

export function getInventory(municipality?: string, signal?: AbortSignal) {
  const query = municipality ? `?${new URLSearchParams({ municipality })}` : "";
  return apiRequest<InventorySummary>(`/inventory/summary${query}`, { signal });
}

export function getMunicipalities(
  signal?: AbortSignal,
  scope: "eligible" | "all" = "eligible",
) {
  return apiRequest<{ municipalities: string[] }>(
    `/inventory/municipalities${scope === "all" ? "?scope=all" : ""}`,
    {
      signal,
    },
  );
}

export function getCheckoutConfig(signal?: AbortSignal) {
  return apiRequest<CheckoutConfig>("/checkout/config", { signal });
}

export function createCheckout(data: CheckoutRequest) {
  return apiRequest<CheckoutResponse>("/checkout", {
    method: "POST",
    body: JSON.stringify(data),
    signal: AbortSignal.timeout(115_000),
  });
}

export function getPurchase(publicId: string, signal?: AbortSignal) {
  return apiRequest<PublicPurchase>(
    `/purchases/${encodeURIComponent(publicId)}`,
    { signal },
  );
}

export function refreshPurchase(publicId: string, signal?: AbortSignal) {
  return apiRequest<PublicPurchase>(
    `/purchases/${encodeURIComponent(publicId)}/refresh`,
    { method: "POST", signal },
  );
}
