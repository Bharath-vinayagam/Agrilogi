"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Navigation, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

// Dynamically import map to avoid SSR issues with Leaflet
const RouteLeafletMap = dynamic(
  () => import("@/components/RouteLeafletMap").then(m => m.RouteLeafletMap),
  { ssr: false, loading: () => <div className="h-[320px] rounded-lg bg-stone-100 animate-pulse" /> }
);

interface RouteStep {
  sequence: number;
  type: "farmer" | "mandi";
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  quantity_kg: number | null;
}

interface RouteResult {
  cluster_id: string;
  total_distance_km: number;
  total_duration_minutes: number;
  traffic_delay_minutes: number;
  total_load_kg: number;
  vehicle_capacity_kg: number;
  capacity_utilization_percent: number;
  route: RouteStep[];
  geometry?: any;
  comparison: {
    label?: string;
    original_distance_km: number;
    optimized_distance_km: number;
    distance_saving_percent: number;
    original_duration_minutes: number;
    optimized_duration_minutes: number;
    time_saving_percent: number;
    sequential_distance_km?: number;
    sequence_saving_percent?: number;
  };
}

interface RouteOptimizationPanelProps {
  clusterId: string;
  farmerCount: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function RouteOptimizationPanel({ clusterId, farmerCount }: RouteOptimizationPanelProps) {
  const [result, setResult] = useState<RouteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  async function handleOptimize() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/route-optimization/cluster/${clusterId}`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
      setExpanded(true);
    } catch (err: any) {
      setError(err.message || "Route optimization failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-river/20 bg-river/5 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Navigation size={15} className="text-river" />
          <span className="text-xs font-bold text-river uppercase tracking-wider">Route Optimization</span>
          {result && (
            <span className="text-[10px] font-semibold text-stone-500">
              {result.total_distance_km} km · {result.total_duration_minutes} min
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {result && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[10px] font-bold text-river hover:underline flex items-center gap-1"
            >
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? "Hide" : "Show"} route
            </button>
          )}
          <button
            onClick={handleOptimize}
            disabled={loading || farmerCount < 2}
            className="focus-ring rounded-lg bg-river px-3 py-1.5 text-[11px] font-bold text-white hover:bg-river/90 disabled:opacity-50 transition-colors"
          >
            {loading ? "Optimizing..." : result ? "Re-optimize" : "Optimize Route"}
          </button>
        </div>
      </div>

      {farmerCount < 2 && (
        <p className="mt-1 text-[10px] text-stone-400 italic">Need at least 2 farmers with GPS to optimize.</p>
      )}

      {error && (
        <div className="mt-2 flex items-center gap-2 rounded-lg bg-chilli/10 px-3 py-2 text-xs text-chilli">
          <AlertTriangle size={13} />
          {error}
        </div>
      )}

      {result && expanded && (
        <div className="mt-3 space-y-3">
          {/* Metrics */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="rounded-lg bg-white border border-stone-100 p-2 text-center">
              <p className="text-[9px] uppercase font-bold text-stone-400">Distance</p>
              <p className="text-sm font-black text-stone-800">{result.total_distance_km} km</p>
            </div>
            <div className="rounded-lg bg-white border border-stone-100 p-2 text-center">
              <p className="text-[9px] uppercase font-bold text-stone-400">Duration</p>
              <p className="text-sm font-black text-stone-800">{result.total_duration_minutes} min</p>
            </div>
            <div className="rounded-lg bg-white border border-stone-100 p-2 text-center">
              <p className="text-[9px] uppercase font-bold text-stone-400">Traffic Delay</p>
              <p className="text-sm font-black text-harvest">+{result.traffic_delay_minutes} min</p>
            </div>
            <div className="rounded-lg bg-white border border-stone-100 p-2 text-center">
              <p className="text-[9px] uppercase font-bold text-stone-400">Load</p>
              <p className="text-sm font-black text-stone-800">{result.capacity_utilization_percent}%</p>
            </div>
          </div>

          {/* Comparison */}
          <div className="rounded-lg bg-white border border-stone-100 p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-bold text-stone-500 uppercase">Original vs Optimized</p>
              <span className="text-[9px] font-semibold text-stone-400">Individual Direct Trips vs Consolidated Route</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <div />
              <div className="font-bold text-stone-500 text-center">Original (Unbundled)</div>
              <div className="font-bold text-river text-center">Optimized (Consolidated)</div>

              <div className="text-stone-600">Distance</div>
              <div className="text-center text-stone-500">{result.comparison.original_distance_km} km</div>
              <div className="text-center font-bold text-river">{result.comparison.optimized_distance_km} km
                <span className="ml-1 text-field font-black">▼{result.comparison.distance_saving_percent}%</span>
              </div>

              <div className="text-stone-600">Duration</div>
              <div className="text-center text-stone-500">{result.comparison.original_duration_minutes} min</div>
              <div className="text-center font-bold text-river">{result.comparison.optimized_duration_minutes} min
                <span className="ml-1 text-field font-black">▼{result.comparison.time_saving_percent}%</span>
              </div>
            </div>
            {result.comparison.sequence_saving_percent !== undefined && result.comparison.sequence_saving_percent > 0 && (
              <p className="mt-2 text-[9px] text-field font-semibold text-right">
                ✨ +{result.comparison.sequence_saving_percent}% extra distance saved by OR-Tools waypoint re-sequencing
              </p>
            )}
          </div>

          {/* Route map */}
          <div className="rounded-lg overflow-hidden border border-stone-100">
            <RouteLeafletMap route={result.route} geometry={result.geometry} />
          </div>

          {/* Pickup sequence */}
          <div className="rounded-lg bg-white border border-stone-100 p-3">
            <p className="text-[10px] font-bold text-stone-500 uppercase mb-2">Pickup Sequence</p>
            <ol className="space-y-1.5">
              {result.route.map((step, idx) => (
                <li key={`${step.type}-${step.id}-${step.sequence ?? idx}`} className="flex items-center gap-2 text-xs">
                  <span className={`h-5 w-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0 ${
                    step.type === "mandi" ? "bg-field text-white" : "bg-river/20 text-river"
                  }`}>
                    {step.sequence}
                  </span>
                  <span className="font-semibold text-stone-700">{step.name}</span>
                  {step.quantity_kg && (
                    <span className="text-stone-400">{step.quantity_kg} kg</span>
                  )}
                  <span className={`ml-auto text-[9px] font-bold ${
                    step.type === "mandi" ? "text-field" : "text-river"
                  }`}>
                    {step.type === "mandi" ? "DESTINATION" : "PICKUP"}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
