import type { Metadata } from "next";
import { OrderStatus } from "@/components/marketplace/order-status";

export const metadata: Metadata = { title: "Tu Orden" };

export default async function SuccessPage({
  searchParams,
}: {
  searchParams: Promise<{ order_id?: string | string[] }>;
}) {
  const query = await searchParams;
  return (
    <OrderStatus
      publicId={typeof query.order_id === "string" ? query.order_id : undefined}
    />
  );
}
