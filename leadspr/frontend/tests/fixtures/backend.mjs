// Test-only upstream. Production pages never import fixtures or substitute fake data.
import { createServer } from "node:http";
import { setTimeout as delay } from "node:timers/promises";

const timestamp = "2026-09-13T15:00:00Z";
const rules = [
  [0, 7, 3000, 30],
  [8, 30, 2100, 20],
  [31, 60, 1200, 10],
  [61, null, 500, 5],
];
let state;
function reset() {
  state = {
    mode: "test",
    inventoryError: false,
    inventoryDelay: 0,
    purchaseDelay: 0,
    purchaseError: false,
    syncError: false,
    checkoutError: false,
    checkoutDelay: 0,
    checkoutCount: 0,
    syncCount: 0,
    orderStatus: "PENDING",
    orders: [],
    active: 20,
    prices: rules.map((rule) => rule[2]),
    pricingError: false,
    leadMode: "success",
    leadDelay: 0,
    leadRequests: 0,
    leadRows: [],
    syncedLeadCount: 0,
  };
}
reset();
function inventory(municipality) {
  const quantities =
    municipality === "Salinas"
      ? [2, 5, 0, 0]
      : municipality === "San Juan"
        ? [3, 0, 1, 0]
        : [6, 10, 4, 0];
  return {
    as_of: timestamp,
    business_date: "2026-09-13",
    tiers: rules.map(([min, max], index) => ({
      price_cents: state.prices[index],
      available_quantity:
        quantities[index] +
        (index === 0 ? state.syncCount + state.syncedLeadCount : 0),
      age_ranges: [{ min_age_days: min, max_age_days: max }],
    })),
  };
}
function syncRun() {
  return {
    id: 1,
    started_at: timestamp,
    completed_at: timestamp,
    status: "SUCCESS",
    rows_received: state.active,
    leads_created: state.syncCount ? 1 : 0,
    leads_updated: 19,
    leads_deactivated: 0,
    leads_reactivated: 0,
    error_message: null,
  };
}
function dashboard() {
  const stock = inventory();
  return {
    stats: {
      active_leads: state.active,
      available_inventory: stock.tiers.reduce(
        (n, t) => n + t.available_quantity,
        0,
      ),
      fulfilled_orders: 1,
      revenue_cents: 4200,
    },
    inventory: stock,
    recent_purchases: [
      {
        public_id: "ORD-TEST0001",
        buyer_name: "Demo Agent",
        municipality: "Salinas",
        requested_quantity: 2,
        total_amount_cents: 4200,
        status: "FULFILLED",
        created_at: timestamp,
      },
    ],
    last_sync: syncRun(),
    payment_mode: state.mode,
    pricing_rules: rules.map(([min, max, , exclusion], index) => ({
      id: index + 1,
      min_age_days: min,
      max_age_days: max,
      price_cents: state.prices[index],
      exclusion_days: exclusion,
      sort_order: index,
      is_active: true,
    })),
  };
}
createServer(async (req, res) => {
  const url = new URL(req.url, "http://127.0.0.1:4319");
  const send = (data, status = 200) => {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify(data));
  };
  const fail = (message, status = 503) =>
    send({ error: { code: "fixture_error", message } }, status);
  let body = "";
  for await (const chunk of req) body += chunk;
  const data = body ? JSON.parse(body) : {};
  if (url.pathname === "/health") return send({ ok: true });
  if (url.pathname === "/__test/reset") {
    reset();
    return send({ ok: true });
  }
  if (url.pathname === "/__test/state") {
    if (req.method === "POST") Object.assign(state, data);
    return send(state);
  }
  if (
    url.pathname.startsWith("/api/v1/admin/") &&
    req.headers.authorization !==
      "Bearer automated-test-token-never-used-in-the-demo"
  )
    return fail("Unauthorized", 401);
  if (url.pathname === "/api/v1/checkout/config")
    return send({ payment_mode: state.mode });
  if (url.pathname === "/api/v1/inventory/municipalities")
    return send({ municipalities: ["Salinas", "San Juan", "Bayamón"] });
  if (url.pathname === "/api/v1/inventory/summary") {
    if (state.inventoryDelay) await delay(state.inventoryDelay);
    if (state.inventoryError)
      return fail("Inventory is temporarily unavailable.");
    return send(inventory(url.searchParams.get("municipality")));
  }
  if (url.pathname === "/api/v1/checkout" && req.method === "POST") {
    state.checkoutCount += 1;
    state.orders.push(data);
    if (state.checkoutDelay) await delay(state.checkoutDelay);
    if (state.checkoutError)
      return fail("Test checkout could not be opened.", 502);
    return send(
      {
        public_id: "ORD-TEST0002",
        checkout_session_id: "cs_test_fixture",
        checkout_url: "https://checkout.stripe.com/c/pay/cs_test_fixture",
      },
      201,
    );
  }
  if (url.pathname === "/api/v1/admin/leads" && req.method === "POST") {
    state.leadRequests += 1;
    if (state.leadDelay) await delay(state.leadDelay);
    if (state.leadMode === "write_error")
      return send({ error: { code: "sheet_write_failed" } }, 502);
    const key = req.headers["idempotency-key"];
    let row = state.leadRows.find((entry) => entry.key === key);
    const appended = !row;
    if (!row) {
      row = { key, ...data };
      state.leadRows.push(row);
    }
    if (state.leadMode === "success") {
      state.active += state.leadRows.length - state.syncedLeadCount;
      state.syncedLeadCount = state.leadRows.length;
    }
    return send(
      {
        external_id: "LEAD-" + key.replaceAll("-", "").toUpperCase(),
        sheet_written: true,
        appended,
        status: state.leadMode === "success" ? "synced" : "sync_pending",
        available: state.leadMode === "success",
        sync_run: syncRun(),
      },
      201,
    );
  }
  if (url.pathname === "/api/v1/admin/dashboard") return send(dashboard());
  if (
    /^\/api\/v1\/admin\/pricing-rules\/[1-4]$/.test(url.pathname) &&
    req.method === "PATCH"
  ) {
    if (state.pricingError) return fail("Pricing service unavailable", 502);
    const index = Number(url.pathname.split("/").pop()) - 1;
    state.prices[index] = data.price_cents;
    return send(dashboard().pricing_rules[index]);
  }
  if (url.pathname === "/api/v1/admin/sync" && req.method === "POST") {
    if (state.syncError)
      return fail("Google Sheets could not be reached.", 502);
    state.syncCount += 1;
    state.active += 1 + state.leadRows.length - state.syncedLeadCount;
    state.syncedLeadCount = state.leadRows.length;
    return send(syncRun());
  }
  if (
    [
      "/api/v1/purchases/ORD-TEST0002",
      "/api/v1/purchases/ORD-TEST0002/refresh",
    ].includes(url.pathname)
  ) {
    if (state.purchaseDelay) await delay(state.purchaseDelay);
    if (state.purchaseError) return fail("Order service is unavailable.");
    if (
      url.pathname.endsWith("/refresh") &&
      req.method === "POST" &&
      state.reconcilePaid
    ) {
      state.orderStatus = "FULFILLED";
      state.reconciliationCount = (state.reconciliationCount || 0) + 1;
    }
    return send({
      public_id: "ORD-TEST0002",
      status: state.orderStatus,
      insurance_type: "Life Insurance",
      municipality: "Salinas",
      requested_quantity: 2,
      price_per_lead_cents: state.orders.at(-1)?.price_per_lead_cents ?? 2100,
      total_amount_cents:
        (state.orders.at(-1)?.price_per_lead_cents ?? 2100) * 2,
      created_at: timestamp,
      paid_at: null,
      fulfilled_at: null,
      email_sent_at:
        state.orderStatus === "FULFILLED" && !state.emailPending
          ? timestamp
          : null,
    });
  }
  return fail("Not found", 404);
}).listen(4319, "127.0.0.1");
