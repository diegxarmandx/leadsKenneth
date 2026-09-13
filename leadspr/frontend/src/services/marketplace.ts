import { apiRequest } from "@/lib/api";
import type { CheckoutRequest, CheckoutResponse, InventorySummary, PublicPurchase } from "@/types/api";

export function getInventory(municipality?: string) {
  const query = municipality ? `?${new URLSearchParams({ municipality })}` : "";
  return apiRequest<InventorySummary>(`/inventory/summary${query}`);
}

export function getMunicipalities() {
  return apiRequest<{ municipalities: string[] }>("/inventory/municipalities");
}

export function createCheckout(data: CheckoutRequest) {
  return apiRequest<CheckoutResponse>("/checkout", { method: "POST", body: JSON.stringify(data) });
}

export function getPurchase(publicId: string) {
  return apiRequest<PublicPurchase>(`/purchases/${encodeURIComponent(publicId)}`);
}
