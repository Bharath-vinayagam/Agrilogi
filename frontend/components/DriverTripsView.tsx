"use client";

import { useEffect, useState } from "react";
import { Package, MapPin, Calendar, CheckCircle, Clock, Truck, IndianRupee, User, Phone } from "lucide-react";
import { supabase } from "@/services/supabase";
import Link from "next/link";

interface TripAssignment {
  id: string;
  cluster_id: string;
  driver_name: string;
  bid_id: string;
  assigned_at: string;
  status: string;
  contract_value: number;
}

interface Order {
  id: string;
  farmer_name: string;
  phone: string;
  crop: string;
  weight_kg: number;
  village: string;
  destination: string;
  pickup_date: string;
  pickup_slot: string;
  shared_cost: number;
  status: string;
  cluster_id: string;
}

interface DriverTripsViewProps {
  user: any;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "In Transit": { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  "Completed": { bg: "bg-green-50", text: "text-green-700", border: "border-green-200" },
  "Assigned": { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  "Cluster Forming": { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200" },
};

export function DriverTripsView({ user }: DriverTripsViewProps) {
  const [activeTrips, setActiveTrips] = useState<TripAssignment[]>([]);
  const [pastTrips, setPastTrips] = useState<TripAssignment[]>([]);
  const [selectedTrip, setSelectedTrip] = useState<TripAssignment | null>(null);
  const [tripOrders, setTripOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTrips();
  }, [user]);

  async function loadTrips() {
    try {
      setError(null);
      const driverName = user?.name || "Driver";

      // Get all trip assignments for this driver
      const { data: trips, error } = await supabase
        .from("trip_assignments")
        .select("*")
        .eq("driver_name", driverName)
        .order("assigned_at", { ascending: false });

      if (error) {
        console.error("Failed to load trips:", error);
        // Check if it's a column missing error
        if (error.message?.includes("column") || error.code === "42703") {
          setError("database_migration_needed");
        } else {
          setError(error.message || "Failed to load trips");
        }
        throw error;
      }

      if (trips) {
        // Separate active and past trips based on status
        const active = trips.filter(t => t.status !== "Completed");
        const past = trips.filter(t => t.status === "Completed");
        
        setActiveTrips(active);
        setPastTrips(past);

        // Auto-select first active trip if available
        if (active.length > 0 && !selectedTrip) {
          selectTrip(active[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load trips:", err);
    } finally {
      setLoading(false);
    }
  }

  async function selectTrip(trip: TripAssignment) {
    setSelectedTrip(trip);
    
    // Load orders for this cluster
    try {
      const { data: orders, error } = await supabase
        .from("orders")
        .select("*")
        .eq("cluster_id", trip.cluster_id);

      if (error) throw error;
      setTripOrders(orders || []);
    } catch (err) {
      console.error("Failed to load trip orders:", err);
      setTripOrders([]);
    }
  }

  function formatDate(dateStr: string) {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { 
      month: "short", 
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  if (loading) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
        <p className="text-stone-500">Loading your trips...</p>
      </div>
    );
  }

  if (error === "database_migration_needed") {
    return (
      <div className="rounded-xl border-2 border-orange-300 bg-orange-50 p-8">
        <div className="text-center mb-4">
          <p className="text-xl font-bold text-orange-700 mb-2">⚠️ Database Update Required</p>
          <p className="text-sm text-orange-600 mb-4">
            The trip_assignments table needs to be updated with new columns.
          </p>
        </div>
        
        <div className="bg-white rounded-lg border border-orange-200 p-4 text-left">
          <p className="text-sm font-bold text-stone-700 mb-2">To fix this, run this SQL in Supabase SQL Editor:</p>
          <pre className="text-xs bg-stone-900 text-green-400 p-3 rounded overflow-x-auto">
{`-- Add missing columns
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS driver_name text;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS cluster_id text;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS bid_id text;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS contract_value integer;
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS status text DEFAULT 'Assigned';
ALTER TABLE trip_assignments ADD COLUMN IF NOT EXISTS assigned_at timestamptz DEFAULT now();

-- Backfill existing data
UPDATE trip_assignments SET driver_name = users.name 
FROM users WHERE trip_assignments.driver_id = users.id AND trip_assignments.driver_name IS NULL;

UPDATE trip_assignments SET cluster_id = bundle_id 
WHERE cluster_id IS NULL AND bundle_id IS NOT NULL;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trip_assignments_driver_name ON trip_assignments(driver_name);
CREATE INDEX IF NOT EXISTS idx_trip_assignments_cluster ON trip_assignments(cluster_id);
CREATE INDEX IF NOT EXISTS idx_trip_assignments_status ON trip_assignments(status);`}
          </pre>
          <p className="text-xs text-stone-500 mt-3">
            📁 Or run the file: <code className="bg-stone-200 px-2 py-1 rounded">database/update_trip_assignments.sql</code>
          </p>
        </div>
        
        <button
          onClick={() => window.location.reload()}
          className="mt-4 w-full rounded-lg bg-orange-600 py-3 font-bold text-white hover:bg-orange-700"
        >
          Refresh After Running SQL
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-red-700 font-bold">Error loading trips</p>
        <p className="text-sm text-red-600 mt-2">{error}</p>
        <button
          onClick={() => loadTrips()}
          className="mt-4 rounded-lg bg-red-600 px-6 py-2 text-sm font-bold text-white hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (activeTrips.length === 0 && pastTrips.length === 0) {
    return (
      <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
        <Truck className="mx-auto mb-3 text-stone-300" size={48} />
        <p className="text-lg font-bold text-stone-700">No Trips Yet</p>
        <p className="mt-1 text-sm text-stone-500">
          Win a bid to get your first trip assignment
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Active Trips Section */}
      {activeTrips.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-black text-soil">Active Trips</h2>
              <p className="text-sm text-stone-500">Your current assigned deliveries</p>
            </div>
            <span className="rounded-full bg-field px-4 py-2 text-sm font-bold text-white">
              {activeTrips.length} Active
            </span>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {activeTrips.map(trip => (
              <button
                key={trip.id}
                onClick={() => selectTrip(trip)}
                className={`rounded-xl border-2 p-4 text-left transition-all hover:shadow-md ${
                  selectedTrip?.id === trip.id
                    ? "border-field bg-field/5"
                    : "border-stone-200 bg-white hover:border-field/50"
                }`}
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="font-mono text-sm font-bold text-soil">{trip.cluster_id}</span>
                  <span className={`rounded-full px-2 py-1 text-xs font-bold ${
                    STATUS_COLORS[trip.status]?.bg || "bg-stone-100"
                  } ${STATUS_COLORS[trip.status]?.text || "text-stone-700"}`}>
                    {trip.status}
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <IndianRupee size={14} className="text-field" />
                    <span className="font-bold text-field">₹{trip.contract_value?.toLocaleString() || "N/A"}</span>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-stone-500">
                    <Calendar size={12} />
                    <span>{formatDate(trip.assigned_at)}</span>
                  </div>

                  {selectedTrip?.id === trip.id && (
                    <Link
                      href="/driver/trip"
                      className="mt-3 block w-full rounded-lg bg-field py-2 text-center text-sm font-bold text-white hover:bg-field/90"
                    >
                      View Trip Details →
                    </Link>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Trip Details */}
      {selectedTrip && tripOrders.length > 0 && (
        <div className="rounded-xl border-2 border-field bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-xl font-black text-soil">
                Trip {selectedTrip.cluster_id}
              </h3>
              <p className="text-sm text-stone-500">
                Assigned on {formatDate(selectedTrip.assigned_at)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-stone-500">Contract Value</p>
              <p className="text-2xl font-black text-field">
                ₹{selectedTrip.contract_value?.toLocaleString() || "N/A"}
              </p>
            </div>
          </div>

          <div className="mb-4 rounded-lg bg-stone-50 p-3">
            <p className="text-xs font-bold text-stone-500 uppercase">Trip Summary</p>
            <div className="mt-2 grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-2xl font-black text-soil">{tripOrders.length}</p>
                <p className="text-xs text-stone-500">Farmers</p>
              </div>
              <div>
                <p className="text-2xl font-black text-soil">
                  {tripOrders.reduce((sum, o) => sum + o.weight_kg, 0)}kg
                </p>
                <p className="text-xs text-stone-500">Total Weight</p>
              </div>
              <div>
                <p className="text-2xl font-black text-soil">
                  {new Set(tripOrders.map(o => o.destination)).size}
                </p>
                <p className="text-xs text-stone-500">Destinations</p>
              </div>
            </div>
          </div>

          <div>
            <h4 className="mb-3 text-sm font-bold uppercase tracking-wider text-stone-500">
              Orders in this Trip ({tripOrders.length})
            </h4>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {tripOrders.map((order, index) => (
                <div
                  key={order.id}
                  className="rounded-lg border border-stone-200 bg-stone-50 p-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-field text-xs font-bold text-white">
                          {index + 1}
                        </span>
                        <span className="font-mono text-sm font-bold text-soil">
                          {order.id}
                        </span>
                      </div>

                      <div className="mt-2 space-y-1">
                        <div className="flex items-center gap-2 text-sm">
                          <User size={14} className="text-stone-400" />
                          <span className="font-semibold text-soil">{order.farmer_name}</span>
                          <Phone size={14} className="text-stone-400 ml-2" />
                          <span className="text-stone-600">{order.phone}</span>
                        </div>

                        <div className="flex items-center gap-2 text-sm">
                          <Package size={14} className="text-stone-400" />
                          <span className="text-stone-600">
                            {order.crop} • {order.weight_kg}kg
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-sm">
                          <MapPin size={14} className="text-stone-400" />
                          <span className="text-stone-600">
                            {order.village} → {order.destination}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-xs text-stone-500">Farmer pays</p>
                      <p className="text-lg font-black text-field">
                        ₹{order.shared_cost}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Past Trips Section */}
      {pastTrips.length > 0 && (
        <div>
          <div className="mb-4">
            <h2 className="text-2xl font-black text-soil">Trip History</h2>
            <p className="text-sm text-stone-500">Your completed deliveries</p>
          </div>

          <div className="space-y-3">
            {pastTrips.map(trip => (
              <button
                key={trip.id}
                onClick={() => selectTrip(trip)}
                className={`w-full rounded-lg border-2 p-4 text-left transition-all hover:shadow-md ${
                  selectedTrip?.id === trip.id
                    ? "border-field bg-field/5"
                    : "border-stone-200 bg-white hover:border-stone-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="text-green-600" size={24} />
                    <div>
                      <p className="font-mono font-bold text-soil">{trip.cluster_id}</p>
                      <p className="text-xs text-stone-500">
                        Completed • {formatDate(trip.assigned_at)}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="text-xs text-stone-500">Earned</p>
                    <p className="text-lg font-black text-field">
                      ₹{trip.contract_value?.toLocaleString() || "N/A"}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
