import { requestJson } from "@/lib/api";
import type {
  DashboardData,
  PricingRule,
  SyncRun,
  LeadEntryInput,
  LeadEntryResponse,
} from "@/types/api";

export const updatePrice = (id: number, price_cents: number) =>
  requestJson<PricingRule>(`/api/operations/pricing-rules/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ price_cents }),
  });

export const getDashboard = (signal?: AbortSignal) =>
  requestJson<DashboardData>("/api/operations/dashboard", { signal });
export const syncSheet = () =>
  requestJson<SyncRun>("/api/operations/sync", {
    method: "POST",
    signal: AbortSignal.timeout(120_000),
  });
export const signIn = (passcode: string) =>
  requestJson<{ authenticated: boolean }>("/api/operations/session", {
    method: "POST",
    body: JSON.stringify({ passcode }),
  });
export const signOut = () =>
  requestJson<{ authenticated: boolean }>("/api/operations/session", {
    method: "DELETE",
  });

export const addLead = (data: LeadEntryInput, requestId: string) =>
  requestJson<LeadEntryResponse>("/api/operations/leads", {
    method: "POST",
    headers: { "Idempotency-Key": requestId },
    body: JSON.stringify(data),
    signal: AbortSignal.timeout(180_000),
  });
