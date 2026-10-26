import type { FarmerOrder } from "@/types";

// Project real lat/lng to SVG canvas coordinates
// SVG viewBox: 0 0 390 240
function projectToSVG(lat: number, lng: number, bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number }) {
  const PADDING = 30;
  const WIDTH = 390 - PADDING * 2;
  const HEIGHT = 240 - PADDING * 2;

  const latRange = bounds.maxLat - bounds.minLat || 0.1;
  const lngRange = bounds.maxLng - bounds.minLng || 0.1;

  const x = PADDING + ((lng - bounds.minLng) / lngRange) * WIDTH;
  const y = PADDING + ((bounds.maxLat - lat) / latRange) * HEIGHT; // invert Y axis
  return { x, y };
}

// Distinct colours per cluster
const CLUSTER_COLORS = ["#4f7d5a", "#2f7f8f", "#d44d3d", "#f6b44b", "#7c5cbf", "#e07b3a"];

export function TacticalMap({ orders }: { orders: FarmerOrder[] }) {
  try {
    if (!orders) {
      return (
        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel min-h-[352px] flex flex-col justify-center items-center">
          <h2 className="text-lg font-bold text-soil mb-4 self-start">Cluster Visualization</h2>
          <div className="flex flex-col items-center gap-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-soil" />
            <p className="text-xs text-stone-500 font-medium animate-pulse">Loading spatial route data...</p>
          </div>
        </section>
      );
    }

    if (orders.length === 0) {
      return (
        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
          <h2 className="text-lg font-bold text-soil">Cluster Visualization</h2>
          <div className="relative mt-4 h-72 w-full rounded-lg bg-[#eef3e9] flex flex-col items-center justify-center border border-dashed border-stone-300">
            <p className="text-xs text-stone-500 font-bold uppercase tracking-wider">No Active Farmer Bookings</p>
            <p className="text-[10px] text-stone-400 mt-1 max-w-[220px] text-center leading-normal">
              Ready to visualize cooperative dispatch clusters once orders are received.
            </p>
          </div>
        </section>
      );
    }

    // Only plot orders with real GPS coordinates (parse numbers safely)
    const geoOrders = orders
      .map(o => ({
        ...o,
        lat: o.lat != null ? Number(o.lat) : undefined,
        lng: o.lng != null ? Number(o.lng) : undefined,
        resolvedClusterId: o.clusterId || (o as any).cluster_id || "unassigned",
      }))
      .filter(o => typeof o.lat === "number" && !isNaN(o.lat) && typeof o.lng === "number" && !isNaN(o.lng));

    const noGeoOrders = orders.filter(o => o.lat == null || o.lng == null || isNaN(Number(o.lat)) || isNaN(Number(o.lng)));

    if (geoOrders.length === 0) {
      return (
        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
          <h2 className="text-lg font-bold text-soil">Cluster Visualization</h2>
          <div className="relative mt-4 h-72 w-full rounded-lg bg-[#eef3e9] flex flex-col items-center justify-center border border-dashed border-stone-300">
            <p className="text-xs text-stone-500 font-bold uppercase tracking-wider">No GPS data yet</p>
            <p className="text-[10px] text-stone-400 mt-1 max-w-[220px] text-center leading-normal">
              {orders.length} order(s) present but no coordinates resolved. Submit orders with a full address to enable map view.
            </p>
          </div>
        </section>
      );
    }

    // Compute lat/lng bounds across all geo orders
    const lats = geoOrders.map(o => o.lat as number);
    const lngs = geoOrders.map(o => o.lng as number);
    const bounds = {
      minLat: Math.min(...lats) - 0.05,
      maxLat: Math.max(...lats) + 0.05,
      minLng: Math.min(...lngs) - 0.05,
      maxLng: Math.max(...lngs) + 0.05,
    };

    // Assign colour per cluster_id
    const clusterIds = Array.from(new Set(geoOrders.map(o => o.resolvedClusterId)));
    const clusterColorMap: Record<string, string> = {};
    clusterIds.forEach((cid, i) => {
      clusterColorMap[cid] = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
    });

    // Project farmer points
    const farmerPoints = geoOrders.map(o => ({
      ...projectToSVG(o.lat as number, o.lng as number, bounds),
      label: o.village?.split(",")[0] || "?",
      farmer: o.farmerName,
      clusterId: o.resolvedClusterId,
      color: clusterColorMap[o.resolvedClusterId],
    }));

    // Destination midpoint (average of all farmer points — proxy for "truck heading out"), clamped to SVG bounds
    const avgX = farmerPoints.reduce((s, p) => s + p.x, 0) / farmerPoints.length;
    const avgY = farmerPoints.reduce((s, p) => s + p.y, 0) / farmerPoints.length;
    const destX = Math.max(35, Math.min(355, avgX + 60));
    const destY = Math.max(35, Math.min(205, avgY - 20));
    const destinations = Array.from(new Set(geoOrders.map(o => o.destination || "Market")));
    const destLabel = destinations.length === 1 ? destinations[0].split(",")[0] : `${destinations.length} Markets`;

    return (
      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel animate-fadeIn">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-bold text-soil">Cluster Visualization</h2>
          {noGeoOrders.length > 0 && (
            <span className="text-[10px] text-stone-400 italic">{noGeoOrders.length} order(s) without GPS not shown</span>
          )}
        </div>

        {/* Cluster legend */}
        {clusterIds.length > 1 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {clusterIds.map((cid, i) => (
              <span key={cid} className="inline-flex items-center gap-1 text-[10px] font-bold text-stone-600 bg-stone-50 border border-stone-200 px-2 py-0.5 rounded-full">
                <span className="h-2 w-2 rounded-full inline-block" style={{ background: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }} />
                {cid === "unassigned" ? "Pending cluster" : cid}
              </span>
            ))}
          </div>
        )}

        <svg className="mt-2 h-72 w-full rounded-lg bg-[#eef3e9]" viewBox="0 0 390 240" role="img" aria-label="Cluster map">
          {/* Routes from each farmer to destination */}
          {farmerPoints.map((pt, i) => (
            <path
              key={`route-${i}`}
              d={`M ${pt.x} ${pt.y} Q ${(pt.x + destX) / 2} ${(pt.y + destY) / 2 - 15} ${destX} ${destY}`}
              fill="none"
              stroke={pt.color}
              strokeWidth="2"
              strokeDasharray="5 4"
              opacity="0.6"
            />
          ))}

          {/* Farmer nodes — coloured by cluster */}
          {farmerPoints.map((pt, i) => (
            <g key={`farmer-${i}`}>
              <circle cx={pt.x} cy={pt.y} r={8} fill={pt.color} stroke="#fff" strokeWidth="1.5" />
              <text fill="#312a24" fontSize="9" fontWeight="700" x={pt.x + 11} y={pt.y + 4}>
                {pt.label}
              </text>
            </g>
          ))}

          {/* Destination node */}
          <g>
            <circle cx={destX} cy={destY} r={10} fill="#d44d3d" stroke="#fff" strokeWidth="2" />
            <text fill="#312a24" fontSize="9" fontWeight="800" x={destX - 30} y={destY - 14}>
              {destLabel}
            </text>
          </g>

          {/* Truck symbol */}
          <g transform={`translate(${(farmerPoints[0]?.x + destX) / 2 - 10}, ${(farmerPoints[0]?.y + destY) / 2 - 8})`}>
            <rect fill="#f6b44b" height="10" rx="2" width="18" />
            <circle cx="4" cy="10" r="2.5" fill="#312a24" />
            <circle cx="14" cy="10" r="2.5" fill="#312a24" />
          </g>
        </svg>
      </section>
    );
  } catch (err) {
    console.error("Map rendering crash:", err);
    return (
      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
        <h2 className="text-lg font-bold text-soil">Cluster Visualization</h2>
        <div className="relative mt-4 h-72 w-full rounded-lg bg-red-50 flex flex-col items-center justify-center border border-red-200">
          <p className="text-xs text-red-500 font-bold uppercase tracking-wider">Map Render Failure</p>
        </div>
      </section>
    );
  }
}
