import { Check, FileSpreadsheet, RefreshCw } from "lucide-react";
import { dateTime, number } from "@/lib/format";
import { Spinner } from "@/components/ui";
import type { SyncRun } from "@/types/api";

export function SheetsSyncCard({
  run,
  syncing,
  refreshing,
  onSync,
}: {
  run: SyncRun | null;
  syncing: boolean;
  refreshing: boolean;
  onSync: () => void;
}) {
  const status =
    run?.status === "SUCCESS"
      ? "Exitosa"
      : run?.status === "FAILED"
        ? "Requiere atención"
        : run?.status === "RUNNING"
          ? "En progreso"
          : "Sin sincronizar";
  return (
    <section className="panel sync-panel">
      <div className="sync-heading">
        <span className="sheets-icon">
          <FileSpreadsheet size={23} aria-hidden="true" />
        </span>
        <div>
          <h2>Sincronización con Google Sheets</h2>
          <p>Tu fuente de información de leads</p>
        </div>
      </div>
      <div className="sync-status-row">
        <span
          className={`status-badge status-${run?.status === "SUCCESS" ? "success" : run?.status === "FAILED" ? "danger" : "pending"}`}
        >
          {run?.status === "SUCCESS" && <Check size={12} aria-hidden="true" />}
          {status}
        </span>
      </div>
      <dl className="sync-details">
        <div className="last-sync">
          <dt>Última Sincronización</dt>
          <dd>
            {run
              ? dateTime(run.completed_at || run.started_at)
              : "Lista para la primera sincronización"}
          </dd>
        </div>
        <div>
          <dt>Filas Recibidas</dt>
          <dd>{run ? number(run.rows_received) : "—"}</dd>
        </div>
        <div>
          <dt>Creados</dt>
          <dd>{run ? number(run.leads_created) : "—"}</dd>
        </div>
        <div>
          <dt>Actualizados</dt>
          <dd>{run ? number(run.leads_updated) : "—"}</dd>
        </div>
        <div>
          <dt>Desactivados</dt>
          <dd>{run ? number(run.leads_deactivated) : "—"}</dd>
        </div>
      </dl>
      <button
        className="button button-secondary sync-button"
        type="button"
        disabled={syncing || refreshing}
        onClick={onSync}
      >
        {syncing ? (
          <Spinner label="Sincronizando con Google Sheets" />
        ) : (
          <RefreshCw size={16} aria-hidden="true" />
        )}
        {syncing ? "Sincronizando..." : "Sincronizar Ahora"}
      </button>
      <p className="sync-caption">
        Actualiza tu hoja de prueba y sincroniza para refrescar el marketplace.
      </p>
    </section>
  );
}
