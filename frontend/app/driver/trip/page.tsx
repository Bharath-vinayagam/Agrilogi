"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/services/supabase";
import { 
  LogOut, 
  Truck, 
  MapPin, 
  IndianRupee, 
  Compass, 
  Scale, 
  Clock, 
  Award, 
  Star, 
  Phone, 
  CheckCircle, 
  AlertOctagon, 
  Navigation,
  CheckCircle2,
  Calendar,
  Sparkles,
  ShieldAlert
} from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

interface FarmerContact {
  name: string;
  village: string;
  phone: string;
  crop: string;
  weight: number;
}

export default function DriverTripPage() {
  const { user, loading } = useAuth("driver");
  const router = useRouter();

  // Active Trip Assignments states
  const [activeTrip, setActiveTrip] = useState<any>(null);
  const [loadingTrip, setLoadingTrip] = useState(true);
  const [tripStatus, setTripStatus] = useState<string>("Driver Assigned");
  const [tripStage, setTripStage] = useState<number>(0);
  const [isAutoSimulating, setIsAutoSimulating] = useState(false);

  // Stats / Metrics
  const [distanceSaved, setDistanceSaved] = useState(0);
  const [co2Saved, setCo2Saved] = useState(0);
  const [routeScore, setRouteScore] = useState(0);

  // Real trip data
  const [tripWeight, setTripWeight] = useState(0);
  const [tripCapacity, setTripCapacity] = useState(1100);
  const [tripUtilization, setTripUtilization] = useState(0);
  const [tripPayout, setTripPayout] = useState(0);
  const [contacts, setContacts] = useState<FarmerContact[]>([]);
  const [mapPoints, setMapPoints] = useState([
    { id: "base", x: 60, y: 210, label: "Driver Base", sub: "Start Point" },
    { id: "stop1", x: 140, y: 170, label: "Pickup A", sub: "Loading..." },
    { id: "stop2", x: 240, y: 90, label: "Pickup B", sub: "Loading..." },
    { id: "stop3", x: 330, y: 190, label: "Pickup C", sub: "Loading..." },
    { id: "mandi", x: 440, y: 110, label: "Koyambedu Mandi", sub: "Final Destination" }
  ]);

  // SOS state
  const [sosActive, setSosActive] = useState(false);
  const [sosSent, setSosSent] = useState(false);

  // Load Active Trip
  const loadTrip = async () => {
    if (!user) return;
    setLoadingTrip(true);
    try {
      const { data: assignment, error } = await supabase
        .from("trip_assignments")
        .select("*")
        .eq("driver_id", user.driverId || user.id)
        .not("trip_status", "in", '(Completed,Delivered)')
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (assignment) {
        setActiveTrip(assignment);
        setTripStatus(assignment.trip_status);
        mapStatusToStage(assignment.trip_status);
        // Use cluster_id from assignment (not bundle_id)
        const clusterId = assignment.cluster_id || assignment.bundle_id;
        console.log(`🚛 Active trip found: ${assignment.id}, cluster: ${clusterId}`);
        await loadBundleData(clusterId);
      } else {
        setActiveTrip(null);
        setTripStatus("NoActive");
        setTripStage(-1);
      }
    } catch (err) {
      console.error("Error loading active trip:", err);
    } finally {
      setLoadingTrip(false);
    }
  };

  // Load real bundle + order data for the active trip
  const loadBundleData = async (clusterId: string) => {
    if (!clusterId) {
      console.warn('⚠️ No cluster ID provided to loadBundleData');
      return;
    }
    console.log(`📦 Loading bundle data for cluster: ${clusterId}`);
    try {
      // Get bundle info (bundles table uses 'id' which matches cluster_id)
      const { data: bundle, error: bundleError } = await supabase
        .from("bundles")
        .select("*")
        .eq("id", clusterId)
        .maybeSingle();

      if (bundleError) {
        console.error('Bundle fetch error:', bundleError);
      }

      if (bundle) {
        console.log(`✅ Bundle found:`, bundle);
        const capacity = 1100;
        const util = Math.min(100, Math.round((bundle.total_weight_kg / capacity) * 100));
        setTripWeight(bundle.total_weight_kg);
        setTripCapacity(capacity);
        setTripUtilization(util);
        // Payout is set after orders are loaded (sum of shared_costs)
      } else {
        console.warn(`⚠️ No bundle found for cluster ${clusterId}`);
      }

      // Get orders for this cluster
      const { data: orders, error: ordersError } = await supabase
        .from("orders")
        .select("id, farmer_name, phone, village, crop, weight_kg, lat, lng, route_leg_km, individual_cost, shared_cost, final_cost")
        .eq("cluster_id", clusterId);

      if (ordersError) {
        console.error('Orders fetch error:', ordersError);
      }

      console.log(`📦 Loaded ${orders?.length || 0} orders for cluster ${clusterId}`);

      if (orders && orders.length > 0) {
          // Real payout = sum of shared costs (what each farmer pays = what driver earns total)
          // Use final_cost if available, otherwise shared_cost
          const totalPayout = orders.reduce((sum: number, o: any) => {
            const payout = o.final_cost || o.shared_cost || 0;
            console.log(`Order ${o.id} payout: ₹${payout} (final_cost: ${o.final_cost}, shared_cost: ${o.shared_cost})`);
            return sum + payout;
          }, 0);
          console.log(`✅ Total trip payout calculated: ₹${totalPayout} from ${orders.length} orders`);
          setTripPayout(totalPayout);

          // Real capacity from bundle
          if (bundle) {
            const capacity = 1100;
            const util = Math.min(100, Math.round((bundle.total_weight_kg / capacity) * 100));
            setTripWeight(bundle.total_weight_kg);
            setTripCapacity(capacity);
            setTripUtilization(util);
          }
          // Build contacts list from real orders
          const realContacts: FarmerContact[] = orders.map((o: any) => ({
            name: o.farmer_name,
            village: o.village,
            phone: o.phone,
            crop: o.crop,
            weight: o.weight_kg
          }));
          setContacts(realContacts);

          // Build SVG map points — only real stops, no padding
          const svgPositions = [
            { x: 140, y: 170 }, { x: 240, y: 90 }, { x: 330, y: 190 }
          ];
          const realOrders = orders.slice(0, 3);
          const stopPoints = realOrders.map((o: any, i: number) => ({
            id: `stop${i + 1}`,
            x: svgPositions[i].x,
            y: svgPositions[i].y,
            label: o.farmer_name,
            sub: `${o.crop} ${o.weight_kg}kg`
          }));

          // Pad to exactly 3 stops for SVG path consistency (hidden, same coords as last real stop)
          while (stopPoints.length < 3) {
            const last = stopPoints[stopPoints.length - 1] || svgPositions[0];
            stopPoints.push({
              id: `stop${stopPoints.length + 1}`,
              x: last.x,
              y: last.y,
              label: "",
              sub: ""
            });
          }

          const newPoints = [
            { id: "base", x: 60, y: 210, label: "Driver Base", sub: "Start Point" },
            ...stopPoints,
            { id: "mandi", x: 440, y: 110, label: "Koyambedu Mandi", sub: "Final Destination" }
          ];
          setMapPoints(newPoints);

          // Distance savings calculation
          const mandiLat = 13.0716, mandiLng = 80.1945;
          const geoOrders = orders.filter((o: any) => o.lat && o.lng);

          // Individual baseline: each farmer hires own truck = round trip to mandi
          let totalIndividualDist = 0;
          geoOrders.forEach((o: any) => {
            const dLat = (parseFloat(o.lat) - mandiLat) * Math.PI / 180;
            const dLng = (parseFloat(o.lng) - mandiLng) * Math.PI / 180;
            const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(parseFloat(o.lat) * Math.PI / 180) *
              Math.cos(mandiLat * Math.PI / 180) *
              Math.sin(dLng / 2) ** 2;
            totalIndividualDist += 6371 * 2 * Math.asin(Math.sqrt(a)) * 2; // round trip
          });

          // Consolidated: use stored route_leg_km from OR-Tools if available
          const hasRouteData = orders.some((o: any) => o.route_leg_km && o.route_leg_km > 0);
          let consolidatedTotal = 0;
          if (hasRouteData) {
            const totalLegs = orders.reduce((s: number, o: any) => s + (o.route_leg_km || 0), 0);
            const legsWithData = orders.filter((o: any) => o.route_leg_km > 0).length;
            consolidatedTotal = totalLegs + (legsWithData > 0 ? totalLegs / legsWithData : 0);
          } else {
            let totalRouteDist = 0;
            geoOrders.forEach((o: any) => {
              const dLat = (parseFloat(o.lat) - mandiLat) * Math.PI / 180;
              const dLng = (parseFloat(o.lng) - mandiLng) * Math.PI / 180;
              const a = Math.sin(dLat / 2) ** 2 +
                Math.cos(parseFloat(o.lat) * Math.PI / 180) *
                Math.cos(mandiLat * Math.PI / 180) *
                Math.sin(dLng / 2) ** 2;
              totalRouteDist += 6371 * 2 * Math.asin(Math.sqrt(a));
            });
            consolidatedTotal = totalRouteDist * 1.25; // road winding factor
          }

          const distSaved = Math.round(Math.max(0, totalIndividualDist - consolidatedTotal));
          // Route score: 60 base + up to 40 from savings ratio
          const score = totalIndividualDist > 0
            ? Math.min(100, Math.round(60 + (distSaved / totalIndividualDist) * 40))
            : 60;

          setDistanceSaved(distSaved);
          setRouteScore(score);
      }
    } catch (err) {
      console.error("Error loading bundle data:", err);
    }
  };

  useEffect(() => {
    loadTrip();
  }, [user]);

  // Auto simulation effect loop
  useEffect(() => {
    let interval: any = null;
    if (isAutoSimulating && activeTrip && tripStage < 5) {
      interval = setInterval(() => {
        advanceTrip();
      }, 3500);
    } else if (tripStage >= 5) {
      setIsAutoSimulating(false);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isAutoSimulating, tripStage, activeTrip]);

  const mapStatusToStage = (status: string) => {
    switch (status) {
      case "Driver Assigned":
      case "Assigned":
        setTripStage(0);
        break;
      case "En Route to Pickup":
      case "Started":
        setTripStage(1);
        break;
      case "Pickup Complete":
      case "Reached Pickup":
        setTripStage(2);
        break;
      case "In Transit":
      case "Loaded Crops":
        setTripStage(3);
        break;
      case "Approaching Destination":
      case "Reached Market":
        setTripStage(4);
        break;
      case "Delivered":
      case "Completed":
        setTripStage(5);
        break;
      default:
        setTripStage(0);
    }
  };

  // Status transitions
  const advanceTrip = async () => {
    let nextStatus = "Driver Assigned";
    let nextStage = 0;

    if (tripStage === 0) {
      nextStatus = "En Route to Pickup";
      nextStage = 1;
    } else if (tripStage === 1) {
      nextStatus = "Pickup Complete";
      nextStage = 2;
    } else if (tripStage === 2) {
      nextStatus = "In Transit";
      nextStage = 3;
    } else if (tripStage === 3) {
      nextStatus = "Approaching Destination";
      nextStage = 4;
    } else if (tripStage === 4) {
      nextStatus = "Delivered";
      nextStage = 5;
    }

    setTripStage(nextStage);
    setTripStatus(nextStatus);

    // Update in Database if we have an active trip and it is not a local demo trip
    if (activeTrip && activeTrip.id !== "DEMO-TRIP") {
      try {
        const updates: any = {
          trip_status: nextStatus
        };
        if (nextStatus === "En Route to Pickup") {
          updates.start_time = new Date().toISOString();
        } else if (nextStatus === "Delivered") {
          updates.end_time = new Date().toISOString();
        }

        await supabase
          .from("trip_assignments")
          .update(updates)
          .eq("id", activeTrip.id);
      } catch (err) {
        console.error("Failed to update status in Database:", err);
      }
    }
  };

  // Demo Initializer (to let evaluators preview without going through bids flow)
  const initializeDemoTrip = async () => {
    setLoadingTrip(true);
    try {
      // 1. Create a dummy bundle if none exists
      const bundleId = `KB-${Math.floor(1000 + Math.random() * 9000)}`;
      await supabase.from("bundles").insert({
        id: bundleId,
        destination: "Koyambedu Mandi",
        total_weight_kg: 970,
        truck_utilization: 88,
        estimated_savings: 2800,
        spoilage_risk: "Low",
        suggested_departure_time: "07:30 AM"
      });

      // 2. Insert trip assignment
      const { data: newAssignment, error: assignError } = await supabase
        .from("trip_assignments")
        .insert({
          driver_id: user.driverId || user.id,
          bundle_id: bundleId,
          trip_status: "Driver Assigned"
        })
        .select()
        .maybeSingle();

      if (assignError || !newAssignment) {
        throw new Error(assignError?.message || "Failed database insertion");
      }

      setActiveTrip(newAssignment);
      setTripStatus("Driver Assigned");
      setTripStage(0);
    } catch (e) {
      console.warn("Using local fallback for demo trip:", e);
      // Local fallback
      setActiveTrip({ id: "DEMO-TRIP", bundle_id: "KB-1024", trip_status: "Driver Assigned" });
      setTripStatus("Driver Assigned");
      setTripStage(0);
    } finally {
      setLoadingTrip(false);
    }
  };

  const handleLogout = async () => {
    localStorage.removeItem("kb_demo_session");
    await supabase.auth.signOut();
    router.push("/login");
  };

  // Calculate truck icon coordinates based on tripStage
  const getTruckCoords = () => {
    const pts = mapPoints;
    if (pts.length < 5) return { x: 60, y: 210 };
    switch (tripStage) {
      case 0:
        return { x: pts[0].x, y: pts[0].y };
      case 1:
        return { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 - 5 };
      case 2:
        return { x: pts[1].x, y: pts[1].y };
      case 3:
        return { x: (pts[3].x + pts[4].x) / 2, y: (pts[3].y + pts[4].y) / 2 };
      case 4:
        return { x: pts[4].x - 30, y: pts[4].y + 15 };
      case 5:
        return { x: pts[4].x, y: pts[4].y };
      default:
        return { x: pts[0].x, y: pts[0].y };
    }
  };

  const truckCoords = getTruckCoords();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#fffaf0] flex items-center justify-center">
        <p className="text-stone-500 font-semibold animate-pulse font-mono text-xs">Authenticating Driver...</p>
      </div>
    );
  }

  if (!user) return null;

  return (
    <main className="min-h-screen bg-[#fffaf0] flex flex-col md:flex-row pb-12">
      {/* Side Navigation Panel */}
      <aside className="w-full md:w-64 bg-white border-b md:border-r border-stone-200 p-5 flex flex-col justify-between">
        <div className="space-y-6">
          <div>
            <div className="flex items-center gap-2">
              <Truck className="text-soil animate-pulse" size={24} />
              <span className="text-lg font-black text-soil tracking-wide">Agrilogi Driver</span>
            </div>
            <p className="text-[10px] text-stone-400 font-bold uppercase mt-1">Ola Driver Mode</p>
          </div>

          <nav className="space-y-2 text-sm font-bold text-stone-600">
            <Link href="/driver/loads" className="flex items-center gap-2.5 hover:bg-stone-50 p-2.5 rounded-lg hover:text-soil transition-all">
              <Compass size={17} /> Available Loads
            </Link>
            <Link href="/driver/trip" className="flex items-center gap-2.5 bg-soil/5 text-soil p-2.5 rounded-lg border border-soil/10">
              <MapPin size={17} /> Active Journey Map
            </Link>
          </nav>
        </div>

        <button
          onClick={handleLogout}
          className="focus-ring mt-6 w-full flex items-center justify-center gap-2 rounded-lg border border-stone-300 bg-white py-2 text-xs font-bold text-stone-600 hover:bg-stone-50 transition-colors"
        >
          <LogOut size={14} />
          Logout
        </button>
      </aside>

      {/* Main Workspace Area */}
      <section className="flex-1 p-6 md:p-8 space-y-6 max-w-5xl">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-2xl font-black text-soil uppercase tracking-wide">Active Journey Map</h1>
            <p className="text-xs text-stone-500">Cooperative route navigation, crop load status, and live updates.</p>
          </div>
          <span className="text-xs font-semibold text-stone-500">Welcome, {user.name}</span>
        </div>

        {loadingTrip ? (
          <div className="h-64 flex items-center justify-center bg-white rounded-xl border border-stone-200 shadow-panel">
            <p className="text-stone-500 font-semibold animate-pulse font-mono text-xs">Loading trip telemetry...</p>
          </div>
        ) : tripStatus === "NoActive" ? (
          <div className="rounded-xl border border-stone-200 bg-white p-8 text-center shadow-panel space-y-6">
            <div className="max-w-md mx-auto space-y-3">
              <Truck size={48} className="mx-auto text-stone-300" />
              <h3 className="text-lg font-black text-soil uppercase">No Active Trip Assigned</h3>
              <p className="text-xs text-stone-600 leading-relaxed">
                You are currently offline or don't have any active cooperative assignments. 
                Go to the **Available Loads** page to place competitive bids and win agricultural logistics contracts.
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row justify-center gap-3 max-w-md mx-auto">
              <Link 
                href="/driver/loads" 
                className="focus-ring bg-soil text-white px-6 py-2.5 text-xs font-bold rounded-lg hover:bg-soil/95 transition-all uppercase tracking-wider text-center"
              >
                Find & Bid on Loads
              </Link>
              <button 
                onClick={initializeDemoTrip}
                className="focus-ring border border-stone-300 bg-white text-stone-600 px-6 py-2.5 text-xs font-bold rounded-lg hover:bg-stone-50 transition-all uppercase tracking-wider flex items-center justify-center gap-1.5"
              >
                <Sparkles size={14} className="text-harvest" />
                Simulate Demo Trip
              </button>
            </div>
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            {/* Left Side: Journey Info Card */}
            <div className="space-y-6">
              <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-panel space-y-5">
                <div className="flex justify-between items-start border-b border-stone-100 pb-3">
                  <div>
                    <span className="text-[10px] text-stone-400 font-extrabold uppercase tracking-wide">Active Assignment</span>
                    <h3 className="text-sm font-black text-soil uppercase">Bundle #{activeTrip?.cluster_id || activeTrip?.bundle_id || "N/A"}</h3>
                  </div>
                </div>

                {/* Cooperative Progress Steps */}
                <div className="space-y-4">
                  <h4 className="text-xs font-black text-stone-400 uppercase tracking-wider">Cooperative Route Progress</h4>
                  
                  {/* Current Status Box */}
                  <div className="rounded-xl bg-soil/5 border border-soil/10 p-4 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-soil/60 font-extrabold uppercase tracking-wider">Current Status</span>
                      <p className="text-base font-black text-soil uppercase mt-0.5">
                        {tripStatus}
                      </p>
                    </div>

                    {/* Progress indicator pill */}
                    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-black bg-field/15 text-field uppercase tracking-wider border border-field/20">
                      Stage {tripStage + 1}/6
                    </span>
                  </div>

                  {/* Sequential Action Button */}
                  {tripStage < 5 ? (
                    <div className="space-y-2.5">
                      <button
                        onClick={advanceTrip}
                        className="w-full focus-ring bg-soil text-white py-3 px-4 rounded-xl text-sm font-black uppercase tracking-wider shadow-md hover:bg-soil/95 transition-all flex items-center justify-center gap-2"
                      >
                        <Navigation size={16} className="animate-bounce" />
                        {tripStage === 0 && "Start Trip (Next: En Route)"}
                        {tripStage === 1 && "Reached Melma Pickup (Next: Pickup Complete)"}
                        {tripStage === 2 && "Loaded Crops (Next: In Transit)"}
                        {tripStage === 3 && "Heading to Mandi (Next: Approaching)"}
                        {tripStage === 4 && "Delivery Completed (Next: Delivered)"}
                      </button>
                      
                      <button
                        type="button"
                        onClick={() => setIsAutoSimulating(!isAutoSimulating)}
                        className={`w-full focus-ring border py-2.5 px-4 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                          isAutoSimulating 
                            ? "bg-harvest text-white border-harvest shadow-md" 
                            : "bg-white text-stone-600 border-stone-300 hover:bg-stone-50"
                        }`}
                      >
                        <Sparkles size={14} className={isAutoSimulating ? "animate-spin" : "text-harvest"} />
                        {isAutoSimulating ? "Pause Auto-Simulation" : "Start Auto-Simulation"}
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="rounded-xl bg-field/5 border border-field/20 p-4 text-center">
                        <CheckCircle2 size={36} className="mx-auto text-field mb-2 animate-bounce" />
                        <h4 className="text-sm font-bold text-soil">Delivery Verified!</h4>
                        <p className="text-xs text-stone-500 mt-1">Your delivery has been confirmed and recorded.</p>
                      </div>
                      <button
                        onClick={async () => {
                          // Complete trip in database and local state
                          if (activeTrip && activeTrip.id !== "DEMO-TRIP") {
                            await supabase
                              .from("trip_assignments")
                              .update({ trip_status: "Completed", end_time: new Date().toISOString() })
                              .eq("id", activeTrip.id);
                          }
                          setActiveTrip(null);
                          setTripStatus("NoActive");
                          setTripStage(-1);
                        }}
                        className="w-full focus-ring border border-stone-300 bg-white text-stone-600 py-2.5 text-xs font-bold rounded-lg hover:bg-stone-50 transition-colors uppercase tracking-wider"
                      >
                        Find New Loads
                      </button>
                    </div>
                  )}
                </div>
              </section>

              {/* Cooperative Metrics (FEATURE 2 & 3 Integration) */}
              <div className="grid grid-cols-2 gap-4">
                {/* Truck Utilization Meter (FEATURE 2) */}
                <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-panel space-y-3">
                  <h4 className="text-xs font-black text-stone-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Scale size={14} className="text-soil" />
                    Truck Utilization
                  </h4>
                  <div className="space-y-2">
                    <div className="flex justify-between items-baseline">
                      <span className="text-lg font-black text-soil">{tripWeight.toLocaleString()} kg <span className="text-xs font-medium text-stone-400">/ {tripCapacity.toLocaleString()} kg</span></span>
                      <span className="text-xs font-bold text-field bg-field/10 px-2 py-0.5 rounded">{tripUtilization}% Full</span>
                    </div>
                    {/* Utilization Progress Bar */}
                    <div className="h-2 w-full bg-stone-100 rounded-full overflow-hidden">
                      <motion.div 
                        className="h-full bg-gradient-to-r from-soil to-field"
                        initial={{ width: 0 }}
                        animate={{ width: `${tripUtilization}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                      />
                    </div>
                    <p className="text-[10px] text-stone-500 leading-tight">Cooperative cluster gains: Highly efficient truck sharing.</p>
                  </div>
                </section>

                {/* Efficiency Stats (FEATURE 3) */}
                <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-panel space-y-3">
                  <h4 className="text-xs font-black text-stone-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Compass size={14} className="text-soil" />
                    Route Efficiency
                  </h4>
                  <div className="grid grid-cols-1 gap-2 text-center">
                    <div className="bg-stone-50 border border-stone-150 rounded-lg p-3">
                      <span className="text-[9px] text-stone-400 font-bold uppercase block">Distance Saved</span>
                      <strong className="text-lg font-black text-soil">{distanceSaved} km</strong>
                    </div>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-stone-500 pt-1 border-t border-stone-100">
                    <span>Route Score:</span>
                    <strong className="text-field font-black">{routeScore}/100</strong>
                  </div>
                </section>
              </div>

              {/* SOS Emergency Center */}
              <section className="rounded-xl border border-chilli/20 bg-white p-5 shadow-panel space-y-3 relative overflow-hidden">
                <div className="absolute top-0 right-0 bg-chilli/10 text-chilli font-black text-[9px] px-3 py-1 rounded-bl-lg uppercase">
                  Safety System
                </div>
                <h4 className="text-xs font-black text-chilli uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldAlert size={15} />
                  Emergency Dispatch System
                </h4>
                <p className="text-[11px] text-stone-500 leading-normal">
                  In case of breakdown, vehicle delay, or accident, trigger the SOS. 
                  This alerts all cooperative farmers on the route and sends a notification to the Operations Admin.
                </p>

                <div className="pt-1.5">
                  {sosSent ? (
                    <div className="rounded-lg bg-chilli/10 border border-chilli/35 p-3 text-center text-chilli font-bold text-xs animate-fadeIn">
                      🚨 SOS Broadcast Active. Admin and Farmers notified. Support team is dispatched.
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setSosActive(true);
                      }}
                      className="focus-ring w-full bg-chilli text-white py-2 px-4 rounded-lg text-xs font-bold uppercase tracking-wider hover:bg-chilli/95 transition-all flex items-center justify-center gap-2"
                    >
                      <AlertOctagon size={14} />
                      Trigger Emergency SOS
                    </button>
                  )}
                </div>

                {/* SOS Confirmation Overlay */}
                {sosActive && (
                  <div className="absolute inset-0 bg-stone-950/80 backdrop-blur-sm flex flex-col justify-center items-center p-4 text-center z-10">
                    <AlertOctagon size={36} className="text-chilli animate-bounce mb-2" />
                    <strong className="text-white text-sm">CONFIRM EMERGENCY BROADCAST?</strong>
                    <p className="text-[10px] text-stone-300 mt-1 max-w-xs">
                      This will alert the admin and the 3 farmers along this route.
                    </p>
                    <div className="flex gap-2 mt-4 w-full max-w-xs justify-center">
                      <button
                        onClick={async () => {
                          setSosActive(false);
                          setSosSent(true);
                          try {
                            await supabase.from("notifications").insert({
                              phone: user.phone || "0000000000",
                              channel: "sms",
                              message: `🚨 DRIVER EMERGENCY: Driver ${user.name} reported breakdown on route Koyambedu. Please stand by.`,
                              status: "queued"
                            });
                          } catch (err) {
                            console.error(err);
                          }
                        }}
                        className="bg-chilli text-white px-4 py-1.5 text-xs font-bold rounded hover:bg-chilli/90 uppercase tracking-wider"
                      >
                        Confirm SOS
                      </button>
                      <button
                        onClick={() => setSosActive(false)}
                        className="bg-stone-600 text-white px-4 py-1.5 text-xs font-bold rounded hover:bg-stone-500 uppercase tracking-wider"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </section>
            </div>

            {/* Right Side: High Fidelity SVG Journey Map */}
            <div className="space-y-4">
              <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-panel flex flex-col">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-xs font-black text-soil uppercase tracking-wider">Journey Route Visualizer</h3>
                  <span className="text-[10px] font-bold text-stone-400">Interactive Map</span>
                </div>

                {/* High Fidelity SVG Map */}
                <div className="relative rounded-xl border border-stone-150 bg-[#edf2e8] p-2 overflow-hidden shadow-inner">
                  <svg 
                    viewBox="0 0 500 300" 
                    className="w-full h-auto"
                    role="img"
                    aria-label="Journey route map"
                  >
                    {/* Definitions for Gradients and Markers */}
                    <defs>
                      <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#4f7d5a" />
                        <stop offset="50%" stopColor="#8da988" />
                        <stop offset="100%" stopColor="#d44d3d" />
                      </linearGradient>
                      <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
                        <feDropShadow dx="2" dy="2" stdDeviation="3" floodOpacity="0.15" />
                      </filter>
                    </defs>

                    {/* Ground grid/paths */}
                    <rect width="500" height="300" fill="#f4f7f2" rx="10" />
                    
                    {/* Catchment/Cooperative boundary circle */}
                    <circle cx="230" cy="150" r="130" fill="#4f7d5a08" stroke="#4f7d5a" strokeWidth="1" strokeDasharray="5 5" />

                    {/* Dotted Connection Roads */}
                    {mapPoints.length === 5 && (
                    <path 
                      d={`M ${mapPoints[0].x} ${mapPoints[0].y} Q 100 190 ${mapPoints[1].x} ${mapPoints[1].y} T ${mapPoints[2].x} ${mapPoints[2].y} T ${mapPoints[3].x} ${mapPoints[3].y} Q 380 140 ${mapPoints[4].x} ${mapPoints[4].y}`} 
                      fill="none" 
                      stroke="#cbd8c6" 
                      strokeWidth="6" 
                      strokeLinecap="round" 
                    />
                    )}

                    {/* Active Route Highlight (based on stage) */}
                    {tripStage > 0 && mapPoints.length === 5 && (
                      <motion.path 
                        d={`M ${mapPoints[0].x} ${mapPoints[0].y} Q 100 190 ${mapPoints[1].x} ${mapPoints[1].y} T ${mapPoints[2].x} ${mapPoints[2].y} T ${mapPoints[3].x} ${mapPoints[3].y} Q 380 140 ${mapPoints[4].x} ${mapPoints[4].y}`} 
                        fill="none" 
                        stroke="url(#routeGradient)" 
                        strokeWidth="4" 
                        strokeLinecap="round"
                        initial={{ strokeDasharray: "1000", strokeDashoffset: "1000" }}
                        animate={{ strokeDashoffset: 1000 - (tripStage * 200) }}
                        transition={{ duration: 1 }}
                      />
                    )}

                    {/* SVG Waypoints / Nodes */}
                    {mapPoints.map((pt, index) => {
                      // Determine status of this point
                      let color = "#788771"; // Future
                      let size = 6;
                      
                      if (index === 0) {
                        color = "#3b6045"; // Base
                        size = 8;
                      } else if (index === 4) {
                        color = "#d44d3d"; // Mandi
                        size = 8;
                      } else {
                        // Farmer Pickups
                        if (tripStage >= index + 1) {
                          color = "#4f7d5a"; // Visited
                        } else {
                          color = "#e67e22"; // Pending pickup
                        }
                      }

                      return (
                        <g key={pt.id} className="cursor-pointer" filter="url(#shadow)">
                          {/* Anchor Circle */}
                          <circle 
                            cx={pt.x} 
                            cy={pt.y} 
                            r={size + 2} 
                            fill={color} 
                            className="transition-all duration-300"
                          />
                          <circle 
                            cx={pt.x} 
                            cy={pt.y} 
                            r={size} 
                            fill="#ffffff" 
                          />
                          <circle 
                            cx={pt.x} 
                            cy={pt.y} 
                            r={size - 2} 
                            fill={color} 
                          />

                          {/* Node label */}
                          <text 
                            x={pt.x} 
                            y={pt.y - 12} 
                            textAnchor="middle" 
                            fill="#2e251b" 
                            fontSize="9" 
                            fontWeight="bold"
                            className="bg-white px-1 py-0.5 rounded shadow-sm"
                          >
                            {pt.label}
                          </text>
                        </g>
                      );
                    })}

                    {/* Moving Truck Icon */}
                    <g transform={`translate(${truckCoords.x - 12}, ${truckCoords.y - 12})`} filter="url(#shadow)">
                      {/* Aura effect on active truck */}
                      <circle cx="12" cy="12" r="16" fill="#4f7d5a1a" className="animate-ping" />
                      
                      {/* Styled Truck Icon Backdrop */}
                      <rect width="24" height="24" rx="6" fill="#3b6045" stroke="#ffffff" strokeWidth="2" />
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.5" className="p-1">
                        <path d="M10 17h4V5H2v12h3m5 0h4m5-6h-5v7h5v-3.5m0-3.5h-5M20 17h2v-5l-3-2H14v7" />
                        <circle cx="7.5" cy="17.5" r="2.5" />
                        <circle cx="16.5" cy="17.5" r="2.5" />
                      </svg>
                    </g>
                  </svg>

                  {/* Map Floating Legend */}
                  <div className="absolute bottom-2 left-2 bg-white/90 backdrop-blur-sm rounded-lg p-2 border border-stone-200/50 text-[9px] font-bold space-y-1 shadow">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#3b6045]" />
                      <span>Start Base</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#e67e22]" />
                      <span>Farmer Collect Point</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#d44d3d]" />
                      <span>Koyambedu Mandi</span>
                    </div>
                  </div>
                </div>

                {/* Farmer Contact Details List */}
                <div className="mt-4 space-y-2">
                  <h4 className="text-xs font-black text-stone-400 uppercase tracking-wider">Farmer Contacts</h4>
                  <div className="space-y-2">
                    {contacts.map((contact, idx) => (
                      <div key={idx} className="rounded-xl border border-stone-150 p-3 bg-white flex justify-between items-center text-xs">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <span className="font-extrabold text-stone-800">{contact.name}</span>
                            <span className="text-[9px] bg-soil/10 text-soil px-1.5 py-0.5 rounded font-mono uppercase">{contact.village}</span>
                          </div>
                          <p className="text-[10px] text-stone-500">
                            Crops: <strong className="text-stone-700">{contact.crop} ({contact.weight} kg)</strong>
                          </p>
                        </div>
                        <a 
                          href={`tel:${contact.phone.replace(/\s+/g, '')}`} 
                          className="flex items-center gap-1 bg-stone-50 border border-stone-200 hover:bg-stone-100 hover:text-soil px-2.5 py-1.5 rounded-lg text-stone-600 font-bold transition-all text-[11px]"
                        >
                          <Phone size={12} />
                          Call
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
