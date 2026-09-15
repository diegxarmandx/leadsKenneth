"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Banknote,
  CheckCheck,
  CircleCheck,
  Layers3,
  LogOut,
  RefreshCw,
  UsersRound,
} from "lucide-react";
import { DemoBadge, Notice, Spinner } from "@/components/ui";
import { AdminSignIn } from "@/components/operations/admin-sign-in";
import { RecentOrders } from "@/components/operations/recent-orders";
import { SheetsSyncCard } from "@/components/operations/sheets-sync-card";
import { AddLead } from "@/components/operations/add-lead";
import { PricingRules } from "@/components/operations/pricing-rules";
import { getDashboard, signOut, syncSheet } from "@/services/operations";
import { ApiError, errorMessage } from "@/lib/api";
import { dateTime, money, number, tierPresentation } from "@/lib/format";
import type { DashboardData } from "@/types/api";

export function Dashboard({
  initiallyAuthenticated,
}: {
  initiallyAuthenticated: boolean;
}) {
  const [authenticated, setAuthenticated] = useState(initiallyAuthenticated);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState<{
    message: string;
    tone: "success" | "error";
  } | null>(null);
  const syncPending = useRef(false);
  const requestVersion = useRef(0);

  const load = useCallback((signal?: AbortSignal) => {
    const version = ++requestVersion.current;
    return getDashboard(signal)
      .then((result) => {
        if (!signal?.aborted && version === requestVersion.current) {
          setData(result);
          setError("");
        }
      })
      .catch((failure: unknown) => {
        if (!signal?.aborted && version === requestVersion.current) {
          if (failure instanceof ApiError && failure.status === 401) {
            setAuthenticated(false);
            setData(null);
          }
          setError(errorMessage(failure));
        }
      })
      .finally(() => {
        if (!signal?.aborted && version === requestVersion.current)
          setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    const controller = new AbortController();
    void load(controller.signal);
    const onFocus = () => {
      if (!syncPending.current) void load(controller.signal);
    };
    window.addEventListener("focus", onFocus);
    return () => {
      controller.abort();
      window.removeEventListener("focus", onFocus);
    };
  }, [authenticated, load]);

  async function sync() {
    if (syncPending.current) return;
    syncPending.current = true;
    setSyncing(true);
    setFeedback(null);
    try {
      const run = await syncSheet();
      setFeedback(
        run.status === "SUCCESS"
          ? {
              tone: "success",
              message: `Sincronización completada. ${number(run.rows_received)} filas recibidas, ${number(run.leads_created)} leads creados, ${number(run.leads_updated)} actualizados y ${number(run.leads_deactivated)} desactivados.`,
            }
          : {
              tone: "error",
              message:
                "La sincronización requiere atención. Es posible que las filas válidas se hayan actualizado. Revisa los campos requeridos y las fechas en la hoja de prueba e intenta nuevamente.",
            },
      );
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        setAuthenticated(false);
        setData(null);
      }
      setFeedback({ tone: "error", message: errorMessage(failure) });
    } finally {
      await load();
      setSyncing(false);
      syncPending.current = false;
    }
  }

  async function logout() {
    try {
      await signOut();
      ++requestVersion.current;
      setAuthenticated(false);
      setData(null);
      setFeedback(null);
      setError("");
    } catch (failure) {
      setError(errorMessage(failure));
    }
  }

  const stats = data
    ? [
        {
          title: "Leads Activos",
          value: number(data.stats.active_leads),
          detail: "Activos en el inventario de origen",
          Icon: UsersRound,
          color: "blue",
        },
        {
          title: "Inventario Disponible",
          value: number(data.stats.available_inventory),
          detail: "Disponibles para comprar",
          Icon: Layers3,
          color: "teal",
        },
        {
          title: "Órdenes Completadas",
          value: number(data.stats.fulfilled_orders),
          detail: "Órdenes con leads asignados",
          Icon: CheckCheck,
          color: "violet",
        },
        {
          title:
            data.payment_mode === "test"
              ? "Ingresos de Prueba"
              : "Ingresos de Órdenes Completadas",
          value: money(data.stats.revenue_cents),
          detail: "Total de las órdenes completadas",
          Icon: Banknote,
          color: "gold",
        },
      ]
    : [];

  return (
    <div className="workspace operations-page">
      <div className="container">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Resumen de la agencia</p>
            <h1>Operaciones FSG</h1>
            <p>
              Una vista clara de tus leads, órdenes y actividad en el
              marketplace.
            </p>
          </div>
          <div className="heading-actions">
            <DemoBadge />
            {authenticated && (
              <button
                className="icon-button"
                onClick={logout}
                aria-label="Cerrar sesión"
                disabled={syncing || adding}
              >
                <LogOut size={18} aria-hidden="true" />
              </button>
            )}
          </div>
        </div>
        {!authenticated ? (
          <AdminSignIn
            onAuthenticated={() => {
              setAuthenticated(true);
              setLoading(true);
              setError("");
            }}
          />
        ) : (
          <>
            <div className="dashboard-toolbar">
              <span>
                <span className="connected-dot" />
                {data
                  ? `Actualizado ${dateTime(data.inventory.as_of)} · Hora de Puerto Rico`
                  : "Conectando con tu marketplace…"}
              </span>
              <button
                type="button"
                className="text-button"
                disabled={loading || syncing || adding}
                onClick={() => {
                  setLoading(true);
                  void load();
                }}
              >
                {loading ? (
                  <Spinner label="Actualizando el panel" />
                ) : (
                  <RefreshCw size={14} aria-hidden="true" />
                )}
                Actualizar
              </button>
            </div>
            {error && (
              <Notice
                action={
                  <button
                    className="text-button"
                    onClick={() => {
                      setLoading(true);
                      void load();
                    }}
                  >
                    Intenta nuevamente
                  </button>
                }
              >
                {error}
              </Notice>
            )}
            {feedback && (
              <Notice tone={feedback.tone}>{feedback.message}</Notice>
            )}
            {!data && loading ? (
              <div role="status" aria-label="Cargando el panel de operaciones">
                <div className="stats-grid">
                  {[0, 1, 2, 3].map((i) => (
                    <div className="stat-card" key={i}>
                      <div className="skeleton skeleton-line" />
                      <div className="skeleton skeleton-price" />
                      <div className="skeleton skeleton-line" />
                    </div>
                  ))}
                </div>
                <div className="panel dashboard-skeleton">
                  <div className="skeleton skeleton-line" />
                  {[0, 1, 2, 3].map((i) => (
                    <div className="skeleton skeleton-row" key={i} />
                  ))}
                </div>
              </div>
            ) : (
              data && (
                <div
                  className={
                    loading
                      ? "dashboard-content refreshing"
                      : "dashboard-content"
                  }
                  aria-busy={loading}
                >
                  <div className="stats-grid">
                    {stats.map(({ title, value, detail, Icon, color }) => (
                      <article className="stat-card" key={title}>
                        <div className="stat-top">
                          <h2>{title}</h2>
                          <span className={`stat-icon stat-${color}`}>
                            <Icon size={19} aria-hidden="true" />
                          </span>
                        </div>
                        <strong className="stat-value">{value}</strong>
                        <p>{detail}</p>
                      </article>
                    ))}
                  </div>
                  <section className="inventory-overview">
                    <div className="section-title">
                      <h2>Inventario de Leads</h2>
                      <span className="section-caption">
                        <CircleCheck size={13} aria-hidden="true" />
                        Disponibilidad actual en Puerto Rico
                      </span>
                    </div>
                    <AddLead
                      today={data.inventory.business_date}
                      disabled={syncing || loading}
                      onBusyChange={setAdding}
                      onSaved={load}
                    />
                    <div className="inventory-grid">
                      {data.inventory.tiers.map((tier) => {
                        const info = tierPresentation(tier);
                        return (
                          <article
                            className={`inventory-card inventory-${info.key}`}
                            key={tier.price_cents}
                          >
                            <div>
                              <h3>{info.name}</h3>
                              <span>{info.age}</span>
                            </div>
                            <strong>
                              {money(tier.price_cents, true)}
                              <small> / lead</small>
                            </strong>
                            <div
                              className={`availability ${tier.available_quantity === 0 ? "empty" : ""}`}
                            >
                              <span aria-hidden="true" />
                              {number(tier.available_quantity)} disponibles
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </section>
                  <div className="operations-grid">
                    <RecentOrders orders={data.recent_purchases} />
                    <SheetsSyncCard
                      run={data.last_sync}
                      syncing={syncing}
                      refreshing={loading || adding}
                      onSync={sync}
                    />
                  </div>
                  <PricingRules
                    rules={data.pricing_rules}
                    disabled={syncing || loading || adding}
                    onSaved={async (rule) => {
                      setData((current) =>
                        current
                          ? {
                              ...current,
                              pricing_rules: current.pricing_rules.map(
                                (item) => (item.id === rule.id ? rule : item),
                              ),
                            }
                          : current,
                      );
                      await load();
                    }}
                  />
                </div>
              )
            )}
          </>
        )}
      </div>
    </div>
  );
}
