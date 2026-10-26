"use client";

import { useEffect, useState } from "react";
import { Calendar, Clock, Package, Scale, MapPin, IndianRupee, AlertCircle, CheckCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface Order {
  id: string;
  farmer_name: string;
  crop: string;
  weight_kg: number;
  village: string;
  destination: string;
  pickup_date: string;
  pickup_slot: string;
  is_time_flexible: boolean;
  shared_cost: number;
  status: string;
}

interface OrderBid {
  id: string;
  driver_name: string;
  amount: number;
  vehicle: string;
  reliability_score: number;
  status: string;
  created_at: string;
}

interface DriverOrderBidViewProps {
  user: any;
}

interface CapacityInfo {
  total_capacity: number;
  confirmed_weight: number;
  pending_weight: number;
  total_committed: number;
  available_capacity: number;
  utilization_percent: number;
  at_capacity: boolean;
  confirmed_orders: number;
  pending_bids: number;
  orders_onboard_now: number;
}

interface TimelineEvent {
  time: string;
  event: string;
  load: number;
  available: number;
  weight_change?: string;
}

const SLOT_EMOJI: Record<string, string> = {
  morning: "🌅",
  afternoon: "☀️",
  evening: "🌆"
};

const SLOT_TIME: Record<string, string> = {
  morning: "6:00 AM - 10:00 AM",
  afternoon: "11:00 AM - 3:00 PM",
  evening: "4:00 PM - 8:00 PM"
};

export function DriverOrderBidView({ user }: DriverOrderBidViewProps) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [orderBids, setOrderBids] = useState<OrderBid[]>([]);
  const [capacityInfo, setCapacityInfo] = useState<CapacityInfo | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [showTimeline, setShowTimeline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState<string>("");
  const [submittingBid, setSubmittingBid] = useState(false);
  const [bidError, setBidError] = useState<string>("");
  const [bidSuccess, setBidSuccess] = useState<string>("");

  useEffect(() => {
    loadAvailableOrders();
    loadCapacityInfo();
    loadTimeline();
  }, []);

  async function loadTimeline() {
    try {
      const driverName = user.name || "Driver";
      const response = await fetch(`${API_BASE}/api/bids/capacity/timeline/${encodeURIComponent(driverName)}`);
      const data = await response.json();
      setTimeline(data);
    } catch (err) {
      console.error("Failed to load timeline:", err);
    }
  }

  async function loadCapacityInfo() {
    try {
      const driverName = user.name || "Driver";
      const response = await fetch(`${API_BASE}/api/bids/capacity/${encodeURIComponent(driverName)}`);
      const data = await response.json();
      setCapacityInfo(data);
    } catch (err) {
      console.error("Failed to load capacity info:", err);
    }
  }

  async function loadAvailableOrders() {
    try {
      // Get all pending orders with time slots
      const response = await fetch(`${API_BASE}/api/bookings`);
      const data = await response.json();
      
      // Filter only Pending/Cluster Forming orders with time slots
      const availableOrders = data.filter((order: any) => 
        (order.status === "Pending" || order.status === "Cluster Forming") &&
        order.pickup_date && order.pickup_slot
      );
      
      setOrders(availableOrders);
    } catch (err) {
      console.error("Failed to load orders:", err);
    } finally {
      setLoading(false);
    }
  }

  async function loadOrderBids(orderId: string) {
    try {
      const response = await fetch(`${API_BASE}/api/bids/order/${orderId}`);
      const data = await response.json();
      setOrderBids(data);
    } catch (err) {
      console.error("Failed to load order bids:", err);
      setOrderBids([]);
    }
  }

  function handleOrderClick(order: Order) {
    setSelectedOrder(order);
    loadOrderBids(order.id);
    setBidError("");
    setBidSuccess("");
    setBidAmount("");
  }

  async function handlePlaceBid() {
    if (!selectedOrder || !bidAmount) {
      setBidError("Please enter a bid amount");
      return;
    }

    if (isSlotClosed(selectedOrder.pickup_date, selectedOrder.pickup_slot)) {
      setBidError("Bidding has closed for this time slot. New bids are no longer accepted.");
      return;
    }

    const amount = parseInt(bidAmount);
    if (isNaN(amount) || amount <= 0) {
      setBidError("Please enter a valid amount");
      return;
    }

    setBidError("");
    setBidSuccess("");
    setSubmittingBid(true);

    try {
      const payload = {
        driver_id: user.id || user.driverId || "unknown",
        driver_name: user.name || "Driver",
        order_id: selectedOrder.id,
        amount: amount,
        vehicle: user.vehicleType || "Mini Truck",
        reliability_score: Math.round(user.reliabilityScore || 94)
      };

      const response = await fetch(`${API_BASE}/api/bids/order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to place bid");
      }

      const newBid = await response.json();
      
      setOrderBids(prev => [newBid, ...prev].sort((a, b) => a.amount - b.amount));
      setBidSuccess(`Bid placed successfully! Your bid: ₹${amount.toLocaleString()}`);
      setBidAmount("");
      
      // Reload capacity after successful bid
      await loadCapacityInfo();
      await loadTimeline();
      
      setTimeout(() => setBidSuccess(""), 5000);
    } catch (err: any) {
      console.error("Failed to place bid:", err);
      setBidError(err.message || "Failed to place bid. Please try again.");
    } finally {
      setSubmittingBid(false);
    }
  }

  function formatDate(dateStr: string) {
    const date = new Date(dateStr);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (date.toDateString() === today.toDateString()) {
      return "Today";
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return "Tomorrow";
    } else {
      return date.toLocaleDateString("en-US", { 
        month: "short", 
        day: "numeric",
        weekday: "short"
      });
    }
  }

  function getClosingDateTime(pickupDate: string, pickupSlot: string): Date | null {
    try {
      const parts = pickupDate.split("-");
      if (parts.length !== 3) return null;
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const date = new Date(year, month, day);

      if (pickupSlot === "morning") {
        // Morning closes at 8:00 PM (20:00) previous day
        date.setDate(date.getDate() - 1);
        date.setHours(20, 0, 0, 0);
      } else if (pickupSlot === "afternoon") {
        // Afternoon closes at 10:00 AM same day
        date.setHours(10, 0, 0, 0);
      } else if (pickupSlot === "evening") {
        // Evening closes at 3:00 PM (15:00) same day
        date.setHours(15, 0, 0, 0);
      } else {
        return null;
      }
      return date;
    } catch {
      return null;
    }
  }

  function isSlotClosed(pickupDate: string, pickupSlot: string): boolean {
    const closingTime = getClosingDateTime(pickupDate, pickupSlot);
    if (!closingTime) return false;
    return new Date() >= closingTime;
  }

  function getClosingTime(pickupDate: string, pickupSlot: string) {
    // Calculate when bidding closes (end of previous slot)
    const slotTimes: Record<string, { prev: string; prevEnd: string }> = {
      morning: { prev: "Evening", prevEnd: "8:00 PM" },
      afternoon: { prev: "Morning", prevEnd: "10:00 AM" },
      evening: { prev: "Afternoon", prevEnd: "3:00 PM" }
    };

    const info = slotTimes[pickupSlot];
    if (!info) return null;

    try {
      const parts = pickupDate.split("-");
      if (parts.length !== 3) return null;
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const date = new Date(year, month, day);

      if (pickupSlot === "morning") {
        // Morning closes at 8 PM previous day
        date.setDate(date.getDate() - 1);
        const prevDateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        return `${formatDate(prevDateStr)} ${info.prevEnd}`;
      } else {
        // Afternoon/Evening close same day
        return `${formatDate(pickupDate)} ${info.prevEnd}`;
      }
    } catch {
      return `${pickupDate} ${info.prevEnd}`;
    }
  }

  // Group orders by date and slot
  const groupedOrders: Record<string, Record<string, Order[]>> = {};
  orders.forEach(order => {
    if (!groupedOrders[order.pickup_date]) {
      groupedOrders[order.pickup_date] = {};
    }
    if (!groupedOrders[order.pickup_date][order.pickup_slot]) {
      groupedOrders[order.pickup_date][order.pickup_slot] = [];
    }
    groupedOrders[order.pickup_date][order.pickup_slot].push(order);
  });

  const hasAlreadyBid = orderBids.some(bid => bid.driver_name === (user.name || "Driver"));

  if (loading) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
        <p className="text-stone-500">Loading available orders...</p>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
        <Package className="mx-auto mb-3 text-stone-300" size={48} />
        <p className="text-lg font-bold text-stone-700">No Available Orders</p>
        <p className="mt-1 text-sm text-stone-500">
          Check back later for new orders
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black text-soil">Available Orders</h2>
          <p className="text-sm text-stone-500">Bid on individual orders that match your route</p>
        </div>
        <div className="flex items-center gap-3">
          {capacityInfo && (
            <>
              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className="rounded-lg border border-field bg-white px-3 py-2 text-sm font-semibold text-field hover:bg-field/5"
              >
                {showTimeline ? "Hide" : "Show"} Schedule
              </button>
              <div className="rounded-lg border-2 border-field bg-field/5 px-4 py-2 text-right">
                <p className="text-xs text-stone-500">Vehicle Capacity</p>
                <p className="text-lg font-black text-soil">
                  {capacityInfo.total_committed} / {capacityInfo.total_capacity} kg
                </p>
                <div className="mt-1 h-2 w-32 overflow-hidden rounded-full bg-stone-200">
                  <div 
                    className={`h-full transition-all ${
                      capacityInfo.utilization_percent >= 90 ? 'bg-red-500' :
                      capacityInfo.utilization_percent >= 70 ? 'bg-orange-500' :
                      'bg-field'
                    }`}
                    style={{ width: `${Math.min(100, capacityInfo.utilization_percent)}%` }}
                  />
                </div>
                <p className="text-xs text-stone-600 mt-1">
                  {capacityInfo.available_capacity}kg available • {capacityInfo.orders_onboard_now} onboard
                </p>
              </div>
            </>
          )}
          <button
            onClick={() => { loadAvailableOrders(); loadCapacityInfo(); loadTimeline(); }}
            className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-semibold hover:bg-stone-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Capacity Timeline */}
      {showTimeline && timeline.length > 0 && (
        <div className="rounded-xl border-2 border-field bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-soil">Your Schedule & Capacity Timeline</h3>
              <p className="text-sm text-stone-500">See when your vehicle capacity frees up</p>
            </div>
            <button
              onClick={() => setShowTimeline(false)}
              className="text-stone-400 hover:text-stone-600"
            >
              ✕
            </button>
          </div>

          <div className="space-y-2">
            {timeline.map((event, index) => {
              const isPickup = event.event.includes("Pickup");
              const isDelivery = event.event.includes("Deliver");
              const isCurrent = event.event === "Current";
              const time = new Date(event.time);
              const timeStr = time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
              const dateStr = time.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              
              return (
                <div
                  key={index}
                  className={`flex items-center gap-4 rounded-lg p-3 ${
                    isCurrent ? 'bg-blue-50 border-2 border-blue-300' :
                    isPickup ? 'bg-orange-50 border border-orange-200' :
                    isDelivery ? 'bg-green-50 border border-green-200' :
                    'bg-stone-50 border border-stone-200'
                  }`}
                >
                  <div className="flex-shrink-0 w-20 text-right">
                    <p className="text-xs font-bold text-stone-500">{dateStr}</p>
                    <p className="text-sm font-bold text-soil">{timeStr}</p>
                  </div>
                  
                  <div className="flex-shrink-0">
                    {isCurrent && <span className="text-2xl">📍</span>}
                    {isPickup && <span className="text-2xl">📦</span>}
                    {isDelivery && <span className="text-2xl">✅</span>}
                  </div>
                  
                  <div className="flex-1">
                    <p className="font-semibold text-soil">{event.event}</p>
                    {event.weight_change && (
                      <p className={`text-xs font-bold ${
                        event.weight_change.startsWith('+') ? 'text-orange-600' : 'text-green-600'
                      }`}>
                        {event.weight_change}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0 text-right">
                    <p className="text-xs text-stone-500">Load</p>
                    <p className="text-lg font-black text-soil">{event.load}kg</p>
                  </div>
                  
                  <div className="flex-shrink-0 text-right">
                    <p className="text-xs text-stone-500">Available</p>
                    <p className={`text-lg font-black ${
                      event.available > 500 ? 'text-field' :
                      event.available > 200 ? 'text-orange-500' :
                      'text-red-500'
                    }`}>
                      {event.available}kg
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0 w-32">
                    <div className="h-2 overflow-hidden rounded-full bg-stone-200">
                      <div 
                        className={`h-full ${
                          (event.load / (event.load + event.available)) >= 0.9 ? 'bg-red-500' :
                          (event.load / (event.load + event.available)) >= 0.7 ? 'bg-orange-500' :
                          'bg-field'
                        }`}
                        style={{ width: `${(event.load / (event.load + event.available || 1)) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3 rounded-lg bg-stone-50 p-3 text-center text-xs">
            <div>
              <span className="text-2xl">📦</span>
              <p className="font-bold text-orange-600 mt-1">Pickup = Load increases</p>
            </div>
            <div>
              <span className="text-2xl">✅</span>
              <p className="font-bold text-green-600 mt-1">Delivery = Capacity frees up</p>
            </div>
            <div>
              <span className="text-2xl">📍</span>
              <p className="font-bold text-blue-600 mt-1">Current position</p>
            </div>
          </div>
        </div>
      )}

      {/* Orders Grouped by Date and Slot */}
      {Object.entries(groupedOrders).map(([date, slotGroups]) => (
        <div key={date} className="space-y-4">
          <div className="flex items-center gap-2">
            <Calendar className="text-soil" size={20} />
            <h3 className="text-lg font-bold text-soil">{formatDate(date)}</h3>
            <span className="text-sm text-stone-500">• {date}</span>
          </div>

          {Object.entries(slotGroups).map(([slot, slotOrders]) => {
            const slotClosed = isSlotClosed(date, slot);
            return (
            <div key={`${date}-${slot}`} className="rounded-xl border border-stone-200 bg-white p-4">
              <div className="mb-3 flex items-center gap-2">
                <span className="text-2xl">{SLOT_EMOJI[slot]}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-bold capitalize text-soil">{slot}</p>
                    {slotClosed && (
                      <span className="rounded-full bg-red-100 border border-red-200 px-2 py-0.5 text-xs font-bold text-red-700">
                        🔴 Bidding Closed
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-stone-500">{SLOT_TIME[slot]}</p>
                  <p className={`text-xs font-semibold mt-1 ${slotClosed ? "text-stone-500" : "text-red-600"}`}>
                    {slotClosed ? `Closed: ${getClosingTime(date, slot)}` : `⏰ Closes: ${getClosingTime(date, slot)}`}
                  </p>
                </div>
                <span className="ml-auto rounded-full bg-soil/10 px-3 py-1 text-xs font-bold text-soil">
                  {slotOrders.length} {slotOrders.length === 1 ? "order" : "orders"}
                </span>
              </div>

              <div className="space-y-2">
                {slotOrders.map(order => (
                  <button
                    key={order.id}
                    onClick={() => handleOrderClick(order)}
                    className={`w-full rounded-lg border-2 p-3 text-left transition-all hover:shadow-md ${
                      selectedOrder?.id === order.id
                        ? "border-field bg-field/5"
                        : "border-stone-200 bg-stone-50 hover:border-field/50"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-soil">{order.id}</span>
                          {order.is_time_flexible && (
                            <span className="rounded-full bg-river/10 px-2 py-0.5 text-xs font-bold text-river">
                              Flexible
                            </span>
                          )}
                          {slotClosed && (
                            <span className="rounded-full bg-stone-200 text-stone-700 px-2 py-0.5 text-xs font-semibold">
                              Closed
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-stone-600">
                          <strong>{order.crop}</strong> • {order.weight_kg} kg
                        </p>
                        <p className="mt-1 flex items-center gap-1 text-xs text-stone-500">
                          <MapPin size={12} />
                          {order.village} → {order.destination}
                        </p>
                        <p className="mt-1 text-xs text-stone-400">
                          Farmer: {order.farmer_name}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-field">₹{order.shared_cost}</p>
                        <p className="text-xs text-stone-500">Base rate</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
            );
          })}
        </div>
      ))}

      {/* Selected Order Details & Bidding */}
      {selectedOrder && (
        <div className="rounded-xl border-2 border-field bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-xl font-black text-soil">Order {selectedOrder.id}</h3>
              <p className="text-sm text-stone-500">
                {formatDate(selectedOrder.pickup_date)} • {selectedOrder.pickup_slot} • {SLOT_TIME[selectedOrder.pickup_slot]}
              </p>
            </div>
            <button
              onClick={() => setSelectedOrder(null)}
              className="text-stone-400 hover:text-stone-600"
            >
              ✕
            </button>
          </div>

          <div className="mb-4 grid gap-3 rounded-lg bg-stone-50 p-4 sm:grid-cols-3">
            <div>
              <p className="text-xs text-stone-500">Crop & Weight</p>
              <p className="text-lg font-black text-soil">{selectedOrder.crop} • {selectedOrder.weight_kg} kg</p>
            </div>
            <div>
              <p className="text-xs text-stone-500">Route</p>
              <p className="text-sm font-bold text-soil">{selectedOrder.village} → {selectedOrder.destination}</p>
            </div>
            <div>
              <p className="text-xs text-stone-500">Base Rate</p>
              <p className="text-lg font-black text-field">₹{selectedOrder.shared_cost}</p>
            </div>
          </div>

          {/* Bid Input - Only show if slot is open and haven't bid yet */}
          {selectedOrder && isSlotClosed(selectedOrder.pickup_date, selectedOrder.pickup_slot) ? (
            <div className="mb-4 rounded-lg bg-stone-100 border border-stone-200 px-4 py-3 text-center">
              <p className="font-bold text-stone-700">🔒 Bidding Closed</p>
              <p className="text-sm text-stone-500 mt-1">
                Bidding for this slot closed at {getClosingTime(selectedOrder.pickup_date, selectedOrder.pickup_slot)}. New bids can no longer be placed.
              </p>
            </div>
          ) : !hasAlreadyBid && (
            <div className="mb-4 space-y-3">
              <div className="flex gap-3">
                <input
                  type="number"
                  step="1"
                  min="0"
                  placeholder="Your bid amount..."
                  value={bidAmount}
                  onChange={(e) => setBidAmount(e.target.value)}
                  className="flex-1 rounded-lg border border-stone-300 px-4 py-3 focus:border-field focus:outline-none"
                  disabled={submittingBid}
                />
                <button 
                  onClick={handlePlaceBid}
                  disabled={submittingBid || !bidAmount}
                  className="rounded-lg bg-field px-6 py-3 font-bold text-white hover:bg-field/90 disabled:bg-stone-300 disabled:cursor-not-allowed"
                >
                  {submittingBid ? "Placing..." : "Place Bid"}
                </button>
              </div>

              {bidError && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  <AlertCircle size={16} />
                  {bidError}
                </div>
              )}

              {bidSuccess && (
                <div className="flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
                  <CheckCircle size={16} />
                  {bidSuccess}
                </div>
              )}
            </div>
          )}

          {/* Already Bid Message */}
          {hasAlreadyBid && (
            <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-center">
              <p className="font-bold text-blue-700">✓ You have already placed a bid on this order</p>
              <p className="text-sm text-blue-600 mt-1">You can only bid once per order</p>
            </div>
          )}

          {/* Bids List */}
          {orderBids.length > 0 && (
            <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
              <h5 className="mb-3 text-sm font-bold uppercase tracking-wider text-stone-500">
                Current Bids ({orderBids.length})
              </h5>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {orderBids.map((bid, index) => {
                  const isLowest = index === 0;
                  const isYourBid = bid.driver_name === (user.name || "Driver");
                  
                  return (
                    <div
                      key={bid.id}
                      className={`flex items-center justify-between rounded-lg p-3 ${
                        isLowest 
                          ? "bg-field/10 border-2 border-field" 
                          : isYourBid
                          ? "bg-blue-50 border border-blue-200"
                          : "bg-white border border-stone-200"
                      }`}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-soil">
                            {isYourBid ? "You" : bid.driver_name}
                          </span>
                          {isLowest && (
                            <span className="rounded-full bg-field px-2 py-0.5 text-xs font-bold text-white">
                              Lowest Bid
                            </span>
                          )}
                          {isYourBid && !isLowest && (
                            <span className="rounded-full bg-blue-500 px-2 py-0.5 text-xs font-bold text-white">
                              Your Bid
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-stone-500 mt-1">
                          {bid.vehicle} • {new Date(bid.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className={`text-lg font-black ${isLowest ? "text-field" : "text-soil"}`}>
                          ₹{bid.amount.toLocaleString()}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
