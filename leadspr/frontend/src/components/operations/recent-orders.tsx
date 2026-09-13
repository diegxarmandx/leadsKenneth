import { ShoppingBag } from "lucide-react";
import { money, number } from "@/lib/format";
import { StatusBadge } from "@/components/operations/status-badge";
import type { RecentPurchase } from "@/types/api";

export function RecentOrders({ orders }: { orders: RecentPurchase[] }) {
  return (
    <section className="panel orders-panel">
      <div className="panel-heading">
        <div>
          <h2>Compras Recientes</h2>
          <p>La actividad más reciente en tu marketplace de leads.</p>
        </div>
        <span className="subtle-badge">
          Últimas {orders.length || "órdenes"}
        </span>
      </div>
      {orders.length ? (
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Compras recientes"
        >
          <table className="data-table orders-table">
            <thead>
              <tr>
                <th scope="col">Orden</th>
                <th scope="col">Comprador</th>
                <th scope="col">Municipio</th>
                <th scope="col" className="numeric">
                  Leads
                </th>
                <th scope="col" className="numeric">
                  Total
                </th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.public_id}>
                  <td>
                    <span className="order-id" title={order.public_id}>
                      {order.public_id}
                    </span>
                  </td>
                  <td className="buyer-cell">{order.buyer_name}</td>
                  <td>{order.municipality || "Todo Puerto Rico"}</td>
                  <td className="numeric">
                    {number(order.requested_quantity)}
                  </td>
                  <td className="numeric amount">
                    {money(order.total_amount_cents)}
                  </td>
                  <td>
                    <StatusBadge status={order.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <ShoppingBag size={29} strokeWidth={1.4} aria-hidden="true" />
          <h3>Tu primera orden abre una nueva oportunidad.</h3>
          <p>Las compras aparecerán aquí cuando un agente inicie el pago.</p>
        </div>
      )}
    </section>
  );
}
