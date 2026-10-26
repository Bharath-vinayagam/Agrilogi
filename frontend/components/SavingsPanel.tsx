"use client";

import { useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FarmerOrder, SavingsPoint } from "@/types";
import { TrendingDown, TrendingUp, Percent, IndianRupee } from "lucide-react";

export function SavingsPanel({
  orders,
  trend,
  selectedOrder: externalSelectedOrder
}: {
  orders: FarmerOrder[];
  trend: SavingsPoint[];
  selectedOrder?: FarmerOrder | null;
}) {
  // Use external selected order if provided
  const activeSelectedOrder = externalSelectedOrder ?? null;

  // Calculate costs based on selected order or all orders
  const ordersToCalculate = activeSelectedOrder ? [activeSelectedOrder] : orders;
  const individual = ordersToCalculate.reduce((sum, order) => sum + order.individualCost, 0);
  const shared = ordersToCalculate.reduce((sum, order) => sum + order.sharedCost, 0);
  const savings = individual - shared;
  const savingsPercentage = individual > 0 ? ((savings / individual) * 100).toFixed(1) : "0.0";

  // Calculate per-farmer savings for farmer list
  const farmerSavingsMap = new Map<string, {
    name: string;
    orders: number;
    individual: number;
    shared: number;
    savings: number;
    percentage: number;
  }>();

  ordersToCalculate.forEach(order => {
    const key = `${order.farmerName}_${order.phone}`;
    if (!farmerSavingsMap.has(key)) {
      farmerSavingsMap.set(key, {
        name: order.farmerName,
        orders: 0,
        individual: 0,
        shared: 0,
        savings: 0,
        percentage: 0
      });
    }
    const farmer = farmerSavingsMap.get(key)!;
    farmer.orders += 1;
    farmer.individual += order.individualCost;
    farmer.shared += order.sharedCost;
    farmer.savings = farmer.individual - farmer.shared;
    farmer.percentage = farmer.individual > 0 ? (farmer.savings / farmer.individual) * 100 : 0;
  });

  const farmerSavingsList = Array.from(farmerSavingsMap.values()).sort((a, b) => b.savings - a.savings);

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h2 className="text-lg font-bold text-soil">💰 Savings Dashboard</h2>
          {activeSelectedOrder && (
            <p className="mt-1 text-xs text-stone-600">
              Order #{activeSelectedOrder.id} • {activeSelectedOrder.crop} • {activeSelectedOrder.weightKg}kg
            </p>
          )}
        </div>
      </div>

      {/* Main Savings Display - Dark Theme */}
      <div className="rounded-xl bg-gradient-to-br from-soil to-stone-900 p-6 text-white shadow-lg mb-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-stone-300">Total Savings</p>
            <p className="text-4xl font-black mt-1">Rs {savings.toLocaleString("en-IN")}</p>
          </div>
          <div className="bg-field/20 rounded-full p-4">
            <TrendingDown className="text-field" size={32} />
          </div>
        </div>

        <div className="flex items-center gap-2 bg-black/20 rounded-lg p-3">
          <Percent className="text-harvest" size={20} />
          <span className="text-2xl font-bold text-harvest">{savingsPercentage}%</span>
          <span className="text-xs text-stone-300">cost reduction from clustering</span>
        </div>
      </div>

      {/* Cost Breakdown Cards */}
      <div className="grid gap-3 sm:grid-cols-2 mb-5">
        <div className="rounded-lg border-2 border-chilli/20 bg-chilli/5 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-chilli/70">Individual Cost</p>
              <p className="text-2xl font-bold text-chilli mt-1">Rs {individual.toLocaleString("en-IN")}</p>
              <p className="text-[10px] text-stone-500 mt-1">Without clustering</p>
            </div>
            <TrendingUp className="text-chilli/40" size={28} />
          </div>
        </div>

        <div className="rounded-lg border-2 border-field/20 bg-field/5 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-field/70">Shared Cost</p>
              <p className="text-2xl font-bold text-field mt-1">Rs {shared.toLocaleString("en-IN")}</p>
              <p className="text-[10px] text-stone-500 mt-1">With clustering</p>
            </div>
            <TrendingDown className="text-field/40" size={28} />
          </div>
        </div>
      </div>

      {/* Savings Trend Chart */}
      {/* <div className="mb-5 rounded-lg border border-stone-200 bg-stone-50 p-4">
        <h3 className="text-sm font-bold text-soil mb-3">📈 Savings Trend</h3>
        <div className="h-40">
          <ResponsiveContainer height="100%" width="100%">
            <AreaChart data={trend}>
              <XAxis dataKey="label" tickLine={false} style={{ fontSize: 11 }} />
              <YAxis tickLine={false} width={44} style={{ fontSize: 11 }} />
              <Tooltip 
                formatter={(value) => [`Rs ${Number(value).toLocaleString("en-IN")}`, "Savings"]} 
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Area dataKey="value" fill="#4f7d5a33" stroke="#4f7d5a" strokeWidth={2} type="monotone" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div> */}

      {/* Farmer-wise Savings List - Dark Cards */}
      <div className="border-t border-stone-200 pt-5">
        <h3 className="text-base font-bold text-soil mb-1">👨‍🌾 Farmer-wise Savings</h3>
        <p className="text-xs text-stone-500 mb-4">
          {activeSelectedOrder
            ? "Savings breakdown for this order"
            : `Showing ${farmerSavingsList.length} farmer${farmerSavingsList.length !== 1 ? 's' : ''}`}
        </p>

        <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
          {farmerSavingsList.length === 0 ? (
            <p className="text-center text-sm text-stone-400 py-6 italic">No savings data available yet</p>
          ) : (
            farmerSavingsList.map((farmer, index) => (
              <div
                key={`${farmer.name}_${index}`}
                className="rounded-lg bg-gradient-to-r from-stone-800 to-stone-700 p-4 text-white shadow-md hover:shadow-lg transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-harvest/20 flex items-center justify-center text-xs font-bold text-harvest">
                      {farmer.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-bold">{farmer.name}</p>
                      <p className="text-[10px] text-stone-400">{farmer.orders} order{farmer.orders !== 1 ? 's' : ''}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-black text-harvest">Rs {farmer.savings.toLocaleString("en-IN")}</p>
                    <p className="text-[10px] text-stone-400">saved</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-[11px]">
                  <div className="flex items-center gap-1 bg-black/20 rounded px-2 py-1">
                    <Percent size={12} className="text-harvest" />
                    <span className="font-bold text-harvest">{farmer.percentage.toFixed(1)}%</span>
                  </div>
                  <div className="flex-1 h-2 bg-black/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-harvest to-field transition-all"
                      style={{ width: `${Math.min(farmer.percentage, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="mt-2 flex justify-between text-[10px] text-stone-400">
                  <span>Individual: Rs {farmer.individual.toLocaleString("en-IN")}</span>
                  <span>Shared: Rs {farmer.shared.toLocaleString("en-IN")}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
