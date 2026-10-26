"use client";

import { useEffect, useState } from "react";
import { Calendar, Clock, Package, Scale, TrendingUp, Users, IndianRupee, AlertCircle } from "lucide-react";
import type { SlotBid } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface TimeSlot {
  date: string;
  slot: string;
  orders: number;
  weight_kg: number;
  estimated_value: number;
  flexible_count: number;
}

interface SlotStatus {
  slot_date: string;
  slot_time: string;
  bidding_open: boolean;
  should_close: boolean;
  closing_time: string | null;
  time_remaining: string | null;
  current_winner: {
    driver_name: string;
    amount: number;
    bid_id: string;
  } | null;
}

interface Order {
  id: string;
  crop: string;
  weight_kg: number;
  village: string;
  destination: string;
  is_time_flexible: boolean;
  shared_cost: number;
}

interface DriverTimeSlotViewProps {
  user: any; // Driver user object with id, name, etc.
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

export function DriverTimeSlotView({ user }: DriverTimeSlotViewProps) {
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  const [slotOrders, setSlotOrders] = useState<Order[]>([]);
  const [slotBids, setSlotBids] = useState<SlotBid[]>([]);
  const [slotStatus, setSlotStatus] = useState<SlotStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState<string>("");
  const [submittingBid, setSubmittingBid] = useState(false);
  const [bidError, setBidError] = useState<string>("");
  const [bidSuccess, setBidSuccess] = useState<string>("");

  useEffect(() => {
    loadSlots();
  }, []);

  async function loadSlots() {
    try {
      const response = await fetch(`${API_BASE}/api/bookings/slots/summary`);
      const data = await response.json();
      setSlots(data);
    } catch (err) {
      console.error("Failed to load slots:", err);
    } finally {
      setLoading(false);
    }
  }

  async function loadSlotOrders(date: string, slot: string) {
    try {
      const response = await fetch(
        `${API_BASE}/api/bookings?pickup_date=${date}&pickup_slot=${slot}`
      );
      const data = await response.json();
      setSlotOrders(data);
      
      // Also load existing bids for this slot
      await loadSlotBids(date, slot);
      
      // Load slot status
      await loadSlotStatus(date, slot);
    } catch (err) {
      console.error("Failed to load slot orders:", err);
    }
  }

  async function loadSlotStatus(date: string, slot: string) {
    try {
      const response = await fetch(
        `${API_BASE}/api/bids/slot/status/${date}/${slot}`
      );
      const data = await response.json();
      setSlotStatus(data);
    } catch (err) {
      console.error("Failed to load slot status:", err);
      setSlotStatus(null);
    }
  }

  async function loadSlotBids(date: string, slot: string) {
    try {
      const response = await fetch(
        `${API_BASE}/api/bids/slot/${date}/${slot}`
      );
      const data = await response.json();
      setSlotBids(data);
    } catch (err) {
      console.error("Failed to load slot bids:", err);
      setSlotBids([]);
    }
  }

  async function handleManualClose() {
    if (!selectedSlot) return;
    
    if (!confirm(`Close bidding for ${selectedSlot.date} ${selectedSlot.slot} slot and assign winner?`)) {
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/api/bids/slot/close/${selectedSlot.date}/${selectedSlot.slot}`,
        { method: "POST" }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to close slot");
      }

      const result = await response.json();
      alert(`✅ ${result.message}`);
      
      // Reload slot status
      await loadSlotStatus(selectedSlot.date, selectedSlot.slot);
      await loadSlotBids(selectedSlot.date, selectedSlot.slot);
    } catch (err: any) {
      console.error("Failed to close slot:", err);
      alert(`❌ Failed to close slot: ${err.message}`);
    }
  }

  async function handlePlaceBid() {
    if (!selectedSlot || !bidAmount) {
      setBidError("Please enter a bid amount");
      return;
    }

    const amount = parseInt(bidAmount);  // Changed to parseInt for integer
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
        pickup_date: selectedSlot.date,
        pickup_slot: selectedSlot.slot,
        amount: amount,  // Now an integer
        vehicle: user.vehicleType || "Mini Truck",
        reliability_score: Math.round(user.reliabilityScore || 94)  // Ensure integer
      };

      const response = await fetch(`${API_BASE}/api/bids/slot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to place bid");
      }

      const newBid = await response.json();
      
      // Update bids list
      setSlotBids(prev => [newBid, ...prev].sort((a, b) => a.amount - b.amount));
      setBidSuccess(`Bid placed successfully! Your bid: ₹${amount.toLocaleString()}`);
      setBidAmount("");
      
      // Clear success message after 5 seconds
      setTimeout(() => setBidSuccess(""), 5000);
    } catch (err: any) {
      console.error("Failed to place bid:", err);
      setBidError(err.message || "Failed to place bid. Please try again.");
    } finally {
      setSubmittingBid(false);
    }
  }

  function handleSlotClick(slot: TimeSlot) {
    setSelectedSlot(slot);
    loadSlotOrders(slot.date, slot.slot);
    setBidError("");
    setBidSuccess("");
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

  // Group slots by date
  const slotsByDate: Record<string, TimeSlot[]> = {};
  slots.forEach(slot => {
    if (!slotsByDate[slot.date]) {
      slotsByDate[slot.date] = [];
    }
    slotsByDate[slot.date].push(slot);
  });

  if (loading) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
        <p className="text-stone-500">Loading available slots...</p>
      </div>
    );
  }

  if (slots.length === 0) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
        <Package className="mx-auto mb-3 text-stone-300" size={48} />
        <p className="text-lg font-bold text-stone-700">No Available Loads</p>
        <p className="mt-1 text-sm text-stone-500">
          Check back later for new pickup slots
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black text-soil">Available Time Slots</h2>
          <p className="text-sm text-stone-500">Choose a slot to see details and place your bid</p>
        </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={loadSlots}
                  className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-semibold hover:bg-stone-50"
                >
                  Refresh
                </button>
                {selectedSlot && slotStatus?.bidding_open && (
                  <button
                    onClick={handleManualClose}
                    className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
                  >
                    🔒 Close Slot (Test)
                  </button>
                )}
              </div>
      </div>

      {/* Time Slots Grouped by Date */}
      {Object.entries(slotsByDate).map(([date, dateSlots]) => (
        <div key={date} className="rounded-xl border border-stone-200 bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <Calendar className="text-soil" size={20} />
            <h3 className="text-lg font-bold text-soil">{formatDate(date)}</h3>
            <span className="text-sm text-stone-500">• {date}</span>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {dateSlots.map((slot) => (
              <button
                key={`${slot.date}-${slot.slot}`}
                onClick={() => handleSlotClick(slot)}
                className={`rounded-xl border-2 p-4 text-left transition-all hover:shadow-md ${
                  selectedSlot?.date === slot.date && selectedSlot?.slot === slot.slot
                    ? "border-field bg-field/5"
                    : "border-stone-200 bg-stone-50 hover:border-field/50"
                }`}
              >
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{SLOT_EMOJI[slot.slot]}</span>
                    <div>
                      <p className="font-bold capitalize text-soil">{slot.slot}</p>
                      <p className="text-xs text-stone-500">{SLOT_TIME[slot.slot]}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-stone-600">
                      <Package size={14} />
                      Orders
                    </span>
                    <strong className="text-soil">{slot.orders}</strong>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-stone-600">
                      <Scale size={14} />
                      Weight
                    </span>
                    <strong className="text-soil">{slot.weight_kg} kg</strong>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-stone-600">
                      <IndianRupee size={14} />
                      Value
                    </span>
                    <strong className="text-field">₹{slot.estimated_value.toLocaleString()}</strong>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-stone-600">
                      <Clock size={14} />
                      Flexible
                    </span>
                    <strong className="text-river">{slot.flexible_count}/{slot.orders}</strong>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-stone-200">
                  <span className="text-xs font-bold uppercase text-field">Click to view details →</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}

      {/* Selected Slot Details */}
      {selectedSlot && slotOrders.length > 0 && (
        <div className="rounded-xl border-2 border-field bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{SLOT_EMOJI[selectedSlot.slot]}</span>
              <div>
                <h3 className="text-xl font-black text-soil">
                  {formatDate(selectedSlot.date)} • {selectedSlot.slot} Slot
                </h3>
                <p className="text-sm text-stone-500">{SLOT_TIME[selectedSlot.slot]}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedSlot(null)}
              className="text-stone-400 hover:text-stone-600"
            >
              ✕
            </button>
          </div>

          {/* Slot Status Banner */}
          {slotStatus && (
            <div className={`mb-4 rounded-lg p-3 ${
              slotStatus.bidding_open 
                ? "bg-green-50 border border-green-200" 
                : "bg-red-50 border border-red-200"
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`font-bold ${slotStatus.bidding_open ? "text-green-700" : "text-red-700"}`}>
                    {slotStatus.bidding_open ? "🟢 Bidding Open" : "🔴 Bidding Closed"}
                  </p>
                  {slotStatus.time_remaining && (
                    <p className="text-sm text-stone-600 mt-1">
                      Closes in: <strong>{slotStatus.time_remaining}</strong>
                    </p>
                  )}
                  {!slotStatus.bidding_open && slotStatus.current_winner && (
                    <p className="text-sm text-stone-600 mt-1">
                      Winner: <strong>{slotStatus.current_winner.driver_name}</strong> at <strong>₹{slotStatus.current_winner.amount.toLocaleString()}</strong>
                    </p>
                  )}
                </div>
                {slotStatus.closing_time && (
                  <p className="text-xs text-stone-500">
                    Closes: {new Date(slotStatus.closing_time).toLocaleString()}
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="mb-4 grid gap-3 sm:grid-cols-4 rounded-lg bg-stone-50 p-4">
            <div>
              <p className="text-xs text-stone-500">Total Orders</p>
              <p className="text-xl font-black text-soil">{selectedSlot.orders}</p>
            </div>
            <div>
              <p className="text-xs text-stone-500">Total Weight</p>
              <p className="text-xl font-black text-soil">{selectedSlot.weight_kg} kg</p>
            </div>
            <div>
              <p className="text-xs text-stone-500">Est. Earnings</p>
              <p className="text-xl font-black text-field">₹{selectedSlot.estimated_value.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-stone-500">Flexible Orders</p>
              <p className="text-xl font-black text-river">{selectedSlot.flexible_count}</p>
            </div>
          </div>

          <h4 className="mb-3 text-sm font-bold uppercase tracking-wider text-stone-500">
            Orders in This Slot
          </h4>

          <div className="space-y-2 max-h-80 overflow-y-auto">
            {slotOrders.map((order) => (
              <div
                key={order.id}
                className="flex items-center justify-between rounded-lg border border-stone-200 bg-stone-50 p-3 hover:bg-stone-100"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-soil">{order.id}</span>
                    {order.is_time_flexible && (
                      <span className="rounded-full bg-river/10 px-2 py-0.5 text-xs font-bold text-river">
                        Flexible
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-stone-600">
                    {order.crop} • {order.weight_kg} kg • {order.village} → {order.destination}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-field">₹{order.shared_cost}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 space-y-3">
            {/* Bid Input Section - Only show if bidding is open */}
            {slotStatus?.bidding_open !== false && (
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
                  {submittingBid ? "Placing..." : "Place Bid on Slot"}
                </button>
              </div>
            )}

            {/* Bidding Closed Message */}
            {slotStatus?.bidding_open === false && (
              <div className="rounded-lg bg-stone-100 border border-stone-300 px-4 py-3 text-center">
                <p className="text-stone-700 font-bold">Bidding for this slot has closed</p>
                <p className="text-sm text-stone-500 mt-1">Winner will be assigned automatically</p>
              </div>
            )}

            {/* Error Message */}
            {bidError && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                <AlertCircle size={16} />
                {bidError}
              </div>
            )}

            {/* Success Message */}
            {bidSuccess && (
              <div className="flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
                ✓ {bidSuccess}
              </div>
            )}

            {/* Current Bids Section */}
            {slotBids.length > 0 && (
              <div className="mt-4 rounded-lg border border-stone-200 bg-stone-50 p-4">
                <h5 className="mb-3 text-sm font-bold uppercase tracking-wider text-stone-500">
                  Current Bids ({slotBids.length})
                </h5>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {slotBids.map((bid, index) => {
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
                            {bid.vehicle} • {new Date(bid.created_at || bid.createdAt || "").toLocaleTimeString()}
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
        </div>
      )}
    </div>
  );
}
