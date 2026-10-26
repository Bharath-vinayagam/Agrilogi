"use client";

import { CalendarClock, CheckCircle2, IndianRupee, PackagePlus, Truck, Smartphone, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { savingsTrend } from "@/services/demoData";
import type { FarmerOrder, Driver } from "@/types";
import { StatusPill } from "@/components/StatusPill";
import { VoiceCallSimulator } from "@/components/VoiceCallSimulator";
import { SavingsPanel } from "@/components/SavingsPanel";
import { useAuth } from "@/hooks/useAuth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const SMS_TYPE_LABEL: Record<string, string> = {
  cluster_created:  "📦 Cluster Ready",
  bid_winner:       "🏆 Bid Won",
  driver_assigned:  "🚚 Driver Assigned",
  registration:     "✅ Registration",
  login:            "🔑 Login",
  order_confirmed:  "✅ Order Confirmed",
  bundle_created:   "📦 Bundle Created",
  trip_update:      "🛣️ Trip Update",
  custom:           "📩 Message",
};

function smsLabel(type: string) {
  return SMS_TYPE_LABEL[type] || "📩 Notification";
}

export function FarmerDashboard() {
  const [orders, setOrders] = useState<FarmerOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [smsMessages, setSmsMessages] = useState<any[]>([]);
  const [smsLoading, setSmsLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<FarmerOrder | null>(null);
  const [driverDetails, setDriverDetails] = useState<Driver | null>(null);
  const { user } = useAuth("farmer");

  async function loadSmsMessages(phone: string) {
    setSmsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/sms/notifications/${encodeURIComponent(phone)}`, {
        cache: "no-store"
      });
      if (res.ok) {
        const data = await res.json();
        setSmsMessages(data);
      }
    } catch (err) {
      console.error("Failed to load SMS messages:", err);
    } finally {
      setSmsLoading(false);
    }
  }

  async function loadOrders() {
    try {
      // Pass the logged-in farmer's phone to filter orders
      const data = await api.getOrders(user?.phone);
      setOrders(data);
      
      // Load driver details if there's an assigned order
      const assignedOrder = data.find((order: FarmerOrder) => order.status === "Driver Assigned");
      if (assignedOrder?.assignedDriver) {
        loadDriverDetails(assignedOrder.assignedDriver);
      } else {
        setDriverDetails(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function loadDriverDetails(driverName: string) {
    try {
      // Fetch all drivers and find the one matching the name
      const drivers = await api.getDrivers();
      const driver = drivers.find((d: Driver) => d.name === driverName);
      setDriverDetails(driver || null);
    } catch (err) {
      console.error("Error loading driver details:", err);
      setDriverDetails(null);
    }
  }

  useEffect(() => {
    if (user?.phone) {
      loadOrders();
      loadSmsMessages(user.phone);
    }
  }, [user]);

  async function addBooking(formData: FormData) {
    const crop = String(formData.get("crop") || "Tomato");
    const weight = Number(formData.get("weight") || 150);
    const village = String(formData.get("village") || "New Village");
    const destination = String(formData.get("destination") || "Koyambedu Mandi");
    const pickupDate = String(formData.get("pickup_date") || "");
    const pickupSlot = String(formData.get("pickup_slot") || "");
    const isTimeFlexible = formData.get("is_time_flexible") === "on";
    
    const payload = {
      farmer_name: user?.name || "Unknown Farmer",
      phone: user?.phone || "",
      village,
      crop,
      weight_kg: weight,
      destination,
      pickup_date: pickupDate || undefined,
      pickup_slot: pickupSlot || undefined,
      is_time_flexible: isTimeFlexible
    };

    try {
      const newOrder = await api.createBooking(payload);
      if (newOrder) {
        setOrders([newOrder, ...orders]);
      }
    } catch (err) {
      console.error(err);
    }
  }

  function handleNewNotification(notif: any) {
    setNotifications((prev) => [notif, ...prev]);
  }

  const assignedOrder = orders.find((order) => order.status === "Driver Assigned");

  return (
    <div className="space-y-5">
      {/* Create Booking - Full Width at Top */}
      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-soil">Create Booking</h2>
            <p className="mt-1 text-sm text-stone-600">Crop, weight, pickup location, and delivery destination.</p>
          </div>
          <PackagePlus className="text-field" size={24} />
        </div>
        <form action={addBooking} className="mt-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <input className="focus-ring rounded-lg border border-stone-300 px-3 py-2" name="crop" placeholder="Crop Type" required />
            <input className="focus-ring rounded-lg border border-stone-300 px-3 py-2" min="1" name="weight" placeholder="Weight kg" type="number" required />
            <button className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-field px-4 py-2 font-semibold text-white" type="submit">
              <CheckCircle2 size={18} />
              Submit
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm"
              name="pickup_date"
              type="date"
              min={new Date().toISOString().split('T')[0]}
              required
            />
            <select className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm" name="pickup_slot" required>
              <option value="">Select Pickup Time</option>
              <option value="morning">🌅 Morning (6:00 AM - 10:00 AM)</option>
              <option value="afternoon">☀️ Afternoon (11:00 AM - 3:00 PM)</option>
              <option value="evening">🌆 Evening (4:00 PM - 8:00 PM)</option>
            </select>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
            <input
              type="checkbox"
              name="is_time_flexible"
              id="is_time_flexible"
              className="h-4 w-4 rounded border-stone-300 text-field focus:ring-field"
              defaultChecked
            />
            <label htmlFor="is_time_flexible" className="text-sm text-stone-700 cursor-pointer flex-1">
              <span className="font-semibold">I'm flexible with timing</span>
              <span className="text-stone-500 block text-xs">Get better rates when the system optimizes your pickup time</span>
            </label>
          </div>
          <input
            className="focus-ring w-full rounded-lg border border-stone-300 px-3 py-2"
            name="village"
            placeholder="Pickup address — e.g. 12/4 Gandhi Street, Melma, Kanchipuram District, Tamil Nadu 631501"
            required
          />
          <input
            className="focus-ring w-full rounded-lg border border-stone-300 px-3 py-2"
            name="destination"
            placeholder="Delivery address — e.g. Koyambedu Market, Chennai, Tamil Nadu"
            required
          />
        </form>
      </section>

      {/* Voice Assistant, Assigned Driver, and SMS Delivery - 3 Columns */}
      <div className="grid gap-5 lg:grid-cols-3">
        {/* Voice Assistant */}
        <VoiceCallSimulator 
          onBookingCreated={loadOrders} 
          onNewNotification={handleNewNotification}
          farmerName={user?.name || "Farmer"}
        />

        {/* Assigned Driver */}
        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
          <h2 className="text-lg font-bold text-soil">Assigned Driver</h2>
          {assignedOrder && driverDetails ? (
            <div className="mt-4 space-y-3 text-sm">
              <p className="flex items-center justify-between rounded-lg bg-stone-50 p-3">
                <span className="inline-flex items-center gap-2 text-stone-600"><Truck size={17} /> Driver</span>
                <strong>{driverDetails.name}</strong>
              </p>
              <p className="flex items-center justify-between rounded-lg bg-stone-50 p-3">
                <span className="text-stone-600">Phone</span>
                <strong>{driverDetails.phone}</strong>
              </p>
              <p className="flex items-center justify-between rounded-lg bg-stone-50 p-3">
                <span className="text-stone-600">Vehicle</span>
                <strong>{driverDetails.vehicleNumber}</strong>
              </p>
              <p className="flex items-center justify-between rounded-lg bg-stone-50 p-3">
                <span className="inline-flex items-center gap-2 text-stone-600"><CalendarClock size={17} /> Pickup</span>
                <strong>{assignedOrder.pickupTime}</strong>
              </p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-stone-500">No driver assigned yet.</p>
          )}
        </section>

        {/* SMS Messages */}
        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Smartphone className="text-river" size={20} />
              <h2 className="text-lg font-bold text-soil">SMS Messages</h2>
            </div>
            <button
              onClick={() => user?.phone && loadSmsMessages(user.phone)}
              className="text-xs text-stone-400 hover:text-soil flex items-center gap-1 transition-colors"
            >
              <RefreshCw size={12} />
              Refresh
            </button>
          </div>
          <div className="space-y-3 max-h-[280px] overflow-y-auto pr-1">
            {smsLoading ? (
              <p className="text-xs text-stone-400 italic text-center py-6 animate-pulse">Loading messages...</p>
            ) : smsMessages.length === 0 ? (
              <p className="text-xs text-stone-400 italic text-center py-6">
                No SMS messages yet. Messages will appear here after clustering or driver assignment.
              </p>
            ) : (
              smsMessages.map((sms: any) => (
                <div key={sms.id} className="rounded-lg border border-stone-200 bg-stone-50 p-3 shadow-sm hover:border-river/30 transition-all">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-bold text-river">{smsLabel(sms.type)}</span>
                    <span className="text-[10px] text-stone-400">
                      {sms.created_at ? new Date(sms.created_at).toLocaleString("en-IN", {
                        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
                      }) : "—"}
                    </span>
                  </div>
                  <p className="text-xs text-stone-700 font-mono whitespace-pre-wrap leading-relaxed">{sms.message}</p>
                  <div className="mt-1.5 flex items-center justify-between">
                    <span className="text-[10px] text-stone-400">To: {sms.phone}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      sms.status === "sent" ? "bg-field/10 text-field" :
                      sms.status === "failed" ? "bg-chilli/10 text-chilli" :
                      "bg-harvest/10 text-harvest"
                    }`}>
                      {sms.status === "sent" ? "✓ Sent" : sms.status === "failed" ? "✗ Failed" : "⏳ Queued"}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {/* My Orders and Savings - Full Width Grid */}
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-soil">My Orders</h2>
            {selectedOrder && (
              <button
                onClick={() => setSelectedOrder(null)}
                className="text-xs font-semibold text-field hover:text-field/80 transition-colors px-3 py-1.5 rounded-lg border border-field/20 hover:bg-field/5"
              >
                📊 View Overall Savings
              </button>
            )}
          </div>
          <div className="mt-4 overflow-x-auto">
            {loading ? (
              <p className="text-sm text-stone-500">Loading orders...</p>
            ) : (
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-stone-500">
                  <tr>
                    <th className="py-2">Booking</th>
                    <th>Crop</th>
                    <th>Village</th>
                    <th>Weight</th>
                    <th>Status</th>
                    <th>Pickup</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr 
                      className={`border-t border-stone-200 cursor-pointer hover:bg-stone-50 transition-colors ${selectedOrder?.id === order.id ? 'bg-field/10' : ''}`}
                      key={order.id}
                      onClick={() => setSelectedOrder(order)}
                      title="Click to view individual savings"
                    >
                      <td className="py-3 font-semibold text-soil">{order.id}</td>
                      <td>{order.crop}</td>
                      <td>{order.village}</td>
                      <td>{order.weightKg} kg</td>
                      <td>
                        <StatusPill status={order.status} />
                      </td>
                      <td>{order.pickupTime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <SavingsPanel orders={orders} trend={savingsTrend} selectedOrder={selectedOrder} />
      </div>
    </div>
  );
}
