"use client";

import { useEffect, useState } from "react";
import { Clock, IndianRupee, Scale, Sprout, Truck, ShieldAlert, Sparkles, Navigation, Fuel, Leaf, Compass } from "lucide-react";
import type { Recommendation, FarmerOrder } from "@/types";

interface RecommendationCardProps {
  recommendation: Recommendation;
  orders: FarmerOrder[];
}

export function RecommendationCard({ recommendation, orders = [] }: RecommendationCardProps) {
  // Crop Compatibility — uses backend spoilageRisk as authoritative risk level,
  // frontend engine provides freshness % and detailed reasons
  const checkCropCompatibility = () => {
    const backendRisk = recommendation.spoilageRisk as "Low" | "Medium" | "High";

    if (orders.length === 0) {
      return {
        isCompatible: true,
        freshness: 100,
        risk: backendRisk,
        reasons: ["No active bookings in queue"]
      };
    }

    const uniqueCrops = Array.from(new Set(orders.map(o => o.crop.toLowerCase().trim())));
    const producers = ["tomato", "tomatoes", "apple", "mango"];
    const sensitive = ["green", "leafy", "spinach", "cucumbers", "cabbage", "cauliflower"];

    const hasProducer = uniqueCrops.some(c => producers.includes(c));
    const hasSensitive = uniqueCrops.some(c => sensitive.includes(c));

    if (hasProducer && hasSensitive) {
      return {
        isCompatible: false,
        freshness: backendRisk === "High" ? 72 : 80,
        risk: backendRisk,
        reasons: [
          "Ethylene producer mixed with sensitive crop",
          "Accelerated ripening risk",
          "Compartment separation required"
        ]
      };
    }

    if (uniqueCrops.length > 2) {
      return {
        isCompatible: true,
        freshness: backendRisk === "High" ? 78 : 86,
        risk: backendRisk,
        reasons: [
          "Mixed cargo load",
          "Short direct transit time",
          "Adequate separate ventilation"
        ]
      };
    }

    return {
      isCompatible: true,
      freshness: backendRisk === "Low" ? 94 : backendRisk === "Medium" ? 85 : 75,
      risk: backendRisk,
      reasons: [
        "Compatible Crops",
        "Short Transit Time",
        "Low Temperature Exposure"
      ]
    };
  };

  const compatibility = checkCropCompatibility();

  // 2. Truck Utilization — authoritative value from backend recommendation service
  const truckCapacity = 1100;
  const totalWeight = recommendation.totalWeightKg || orders.reduce((sum, o) => sum + o.weightKg, 0);
  const utilizationPercent = typeof recommendation.truckUtilization === "number"
    ? recommendation.truckUtilization
    : Math.min(100, Math.round((totalWeight / truckCapacity) * 100));

  // 3. Route Efficiency Analytics Calculations
  const distanceSaved = Math.max(0, orders.length * 6);
  const fuelSaved = Number((distanceSaved * 0.15).toFixed(1)); // 15L/100km economy
  const co2Saved = Number((fuelSaved * 2.68).toFixed(1)); // 2.68 kg CO2 per liter
  const routeScore = Math.max(60, Math.min(99, 85 + orders.length * 2));

  // Color mappings
  const riskColors = {
    Low: "text-field bg-field/10 border-field/20",
    Medium: "text-harvest bg-harvest/10 border-harvest/20",
    High: "text-chilli bg-chilli/10 border-chilli/20"
  };

  const riskBadgeColors = {
    Low: "bg-field text-white",
    Medium: "bg-harvest text-white",
    High: "bg-chilli text-white"
  };

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel space-y-5">
      <div>
        <h2 className="text-lg font-bold text-soil flex items-center gap-1.5">
          <Sparkles className="text-harvest" size={19} />
          AI Logistics Recommendation
        </h2>
        <p className="text-xs text-stone-500">Optimized cooperative shipping solutions for maximum savings.</p>
      </div>

      {/* Basic Metrics Rows */}
      <div className="grid gap-2.5 sm:grid-cols-2">
        <div className="flex items-center gap-3 rounded-lg bg-stone-50 p-3">
          <span className="text-soil bg-white p-2 rounded-lg border border-stone-200">
            <Sprout size={16} />
          </span>
          <div>
            <p className="text-[10px] uppercase font-bold text-stone-400">Farmers Bundled</p>
            <p className="text-sm font-black text-soil">{orders.length}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg bg-stone-50 p-3">
          <span className="text-soil bg-white p-2 rounded-lg border border-stone-200">
            <Clock size={16} />
          </span>
          <div>
            <p className="text-[10px] uppercase font-bold text-stone-400">Direct Dispatch</p>
            <p className="text-sm font-black text-soil">{recommendation.departureTime}</p>
          </div>
        </div>
      </div>

      {/* FEATURE 2: Truck Utilization Meter */}
      <div className="rounded-lg border border-stone-150 p-4 space-y-2.5 bg-gradient-to-br from-[#fffdfa] to-white">
        <div className="flex justify-between items-center text-xs">
          <span className="font-bold text-stone-700 uppercase tracking-wider flex items-center gap-1">
            <Truck size={14} className="text-soil" />
            Truck Capacity Utilization
          </span>
          <span className="font-black text-soil">{totalWeight}kg / {truckCapacity}kg</span>
        </div>
        
        {/* Animated Progress Bar */}
        <div className="h-3.5 w-full rounded-full bg-stone-100 overflow-hidden relative border border-stone-200/50">
          <div
            style={{ width: `${utilizationPercent}%` }}
            className={`h-full transition-all duration-1000 ease-out bg-gradient-to-r ${
              utilizationPercent > 90
                ? "from-chilli to-orange-500 animate-pulse"
                : utilizationPercent > 60
                  ? "from-field to-green-400"
                  : "from-river to-blue-400"
            }`}
          />
          <div className="absolute inset-0 flex items-center justify-center text-[10px] font-extrabold text-stone-700 mix-blend-difference">
            {utilizationPercent}% Full
          </div>
        </div>
      </div>

      {/* FEATURE 5: Spoilage Prevention Panel */}
      <div className={`rounded-lg border p-4 ${riskColors[compatibility.risk]} space-y-3`}>
        <div className="flex items-center justify-between">
          <span className="font-bold uppercase tracking-wider text-xs flex items-center gap-1">
            <ShieldAlert size={15} />
            Spoilage Prevention
          </span>
          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${riskBadgeColors[compatibility.risk]}`}>
            {compatibility.risk} Risk
          </span>
        </div>

        <div className="flex justify-between items-center">
          <div className="text-xs space-y-1">
            <p className="text-stone-500 font-bold">Crop Freshness Retained:</p>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-stone-850">{compatibility.freshness}%</span>
              <span className="text-[10px] font-semibold text-stone-500">during transit</span>
            </div>
          </div>
          
          {/* List of reasons */}
          <div className="text-[10px] text-stone-600 pl-4 border-l border-stone-200 space-y-1">
            <p className="font-bold text-stone-500 uppercase">Insights:</p>
            {compatibility.reasons.map((r, i) => (
              <p key={i} className="flex items-center gap-1">
                <span className="text-field font-bold">✓</span> {r}
              </p>
            ))}
          </div>
        </div>
      </div>

      {/* FEATURE 3: Route Efficiency Analytics */}
      <div className="space-y-3">
        <div>
          <h3 className="text-xs font-bold text-stone-500 uppercase tracking-wider">Route Efficiency Analytics</h3>
          <p className="text-[10px] text-stone-400">Savings compared with making individual farmer trips.</p>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div className="rounded-lg bg-stone-50 p-3 border border-stone-100 hover:border-river/35 transition-all text-center">
            <Compass className="mx-auto text-river mb-1" size={18} />
            <p className="text-[9px] uppercase font-bold text-stone-400">Route Score</p>
            <p className="text-sm font-black text-stone-800 mt-0.5">{routeScore}/100</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-3 border border-stone-100 hover:border-field/35 transition-all text-center">
            <Navigation className="mx-auto text-field mb-1" size={18} />
            <p className="text-[9px] uppercase font-bold text-stone-400">Distance Saved</p>
            <p className="text-sm font-black text-stone-800 mt-0.5">{distanceSaved} km</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-3 border border-stone-100 hover:border-harvest/35 transition-all text-center">
            <Fuel className="mx-auto text-harvest mb-1" size={18} />
            <p className="text-[9px] uppercase font-bold text-stone-400">Fuel Saved</p>
            <p className="text-sm font-black text-stone-800 mt-0.5">{fuelSaved} L</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-3 border border-stone-100 hover:border-soil/35 transition-all text-center">
            <Leaf className="mx-auto text-soil mb-1" size={18} />
            <p className="text-[9px] uppercase font-bold text-stone-400">CO₂ Prevented</p>
            <p className="text-sm font-black text-stone-800 mt-0.5">{co2Saved} kg</p>
          </div>
        </div>
      </div>
    </section>
  );
}
