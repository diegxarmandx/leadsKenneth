export type PurchaseStatus =
  "PENDING" | "PAID" | "FULFILLED" | "FAILED" | "FULFILLMENT_FAILED";

export type InventorySummary = {
  as_of: string;
  business_date: string;
  tiers: Array<{
    price_cents: number;
    available_quantity: number;
    age_ranges: Array<{ min_age_days: number; max_age_days: number | null }>;
  }>;
};

export type CheckoutRequest = {
  buyer_name: string;
  buyer_email: string;
  buyer_phone?: string;
  insurance_type?: "Life Insurance";
  municipality?: string;
  price_per_lead_cents: number;
  quantity: number;
};

export type CheckoutResponse = {
  public_id: string;
  checkout_session_id: string;
  checkout_url: string;
};

export type PublicPurchase = {
  public_id: string;
  status: PurchaseStatus;
  insurance_type: string;
  municipality: string | null;
  requested_quantity: number;
  price_per_lead_cents: number;
  total_amount_cents: number;
  created_at: string;
  paid_at: string | null;
  fulfilled_at: string | null;
  email_sent_at: string | null;
};

export type InventoryTier = InventorySummary["tiers"][number];
export type CheckoutConfig = { payment_mode: "test" | "live" | "unconfigured" };
export type SyncRun = {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: "RUNNING" | "SUCCESS" | "FAILED";
  rows_received: number;
  leads_created: number;
  leads_updated: number;
  leads_deactivated: number;
  leads_reactivated: number;
  error_message: string | null;
};
export type PricingRule = {
  id: number;
  min_age_days: number;
  max_age_days: number | null;
  price_cents: number;
  exclusion_days: number;
  sort_order: number;
  is_active: boolean;
};
export type RecentPurchase = Pick<
  PublicPurchase,
  | "public_id"
  | "municipality"
  | "requested_quantity"
  | "total_amount_cents"
  | "status"
  | "created_at"
> & { buyer_name: string };
export type DashboardData = {
  stats: {
    active_leads: number;
    available_inventory: number;
    fulfilled_orders: number;
    revenue_cents: number;
  };
  inventory: InventorySummary;
  recent_purchases: RecentPurchase[];
  last_sync: SyncRun | null;
  pricing_rules: PricingRule[];
  payment_mode: CheckoutConfig["payment_mode"];
};

export type LeadEntryInput = {
  first_name: string;
  last_name: string | null;
  phone: string;
  email: string | null;
  municipality: string;
  lead_date: string;
};
export type LeadEntryResponse = {
  external_id: string;
  sheet_written: true;
  appended: boolean;
  status: "synced" | "sync_pending";
  available: boolean;
  sync_run: SyncRun | null;
};
