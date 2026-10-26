import type { OrderStatus } from "@/types";

const toneByStatus: Record<string, string> = {
  Pending: "bg-amber-100 text-amber-800",
  "Awaiting Cluster": "bg-amber-100 text-amber-800",
  "Cluster Forming": "bg-sky-100 text-sky-800",
  "Driver Assigned": "bg-emerald-100 text-emerald-800",
  "In Transit": "bg-river/15 text-river",
  Completed: "bg-stone-200 text-stone-700",
  "Bidding Closed": "bg-rose-100 text-rose-800",
  Expired: "bg-stone-200 text-stone-600",
  Leading: "bg-field/15 text-field",
  Open: "bg-stone-200 text-stone-700",
  Accepted: "bg-chilli/15 text-chilli"
};

export function StatusPill({ status }: { status: string }) {
  const tone = toneByStatus[status] || "bg-stone-100 text-stone-700";
  return (
    <span className={`inline-flex min-w-24 justify-center rounded-full px-3 py-1 text-xs font-semibold ${tone}`}>
      {status}
    </span>
  );
}

