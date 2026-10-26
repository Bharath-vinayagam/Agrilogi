"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/services/supabase";
import { LogOut, Truck, Scale, Sprout, MapPin, IndianRupee, Compass, Clock, Award, Star, Bell, ShieldAlert, CheckCircle, X } from "lucide-react";
import Link from "next/link";
import { DriverTripsView } from "@/components/DriverTripsView";
import { calculateDriverTripCost } from "@/services/pricingConfig";

interface BidEvent {
  driverName: string;
  vehicle: string;
  amount: number;
  reliability: number;
  timestamp: string;
}

export default function DriverLoadsPage() {
  const { user, loading } = useAuth("driver");
  const router = useRouter();

  // View mode toggle: 'bundles' or 'trips' - Default to bundles (clusters)
  const [viewMode, setViewMode] = useState<'bundles' | 'trips'>('bundles');

  // Active load state (defaults to mock KB1024 if db bundles empty)
  const [bundles, setBundles] = useState<any[]>([]);
  const [selectedBundle, setSelectedBundle] = useState<any>(null);
  
  // Bidding states
  const [driverBid, setDriverBid] = useState<string>("");
  const [bidsFeed, setBidsFeed] = useState<BidEvent[]>([]);
  const [biddingActive, setBiddingActive] = useState(false);
  const [isLowest, setIsLowest] = useState(true);
  const [lowestBidValue, setLowestBidValue] = useState<number>(Infinity);
  
  // Simulated competitor state
  const [compStep, setCompStep] = useState(0);
  const compTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Per-bundle state mapping to prevent stale state issues and enable switching
  const [bundleStates, setBundleStates] = useState<Record<string, {
    driverBid: string;
    bidsFeed: BidEvent[];
    biddingActive: boolean;
    isLowest: boolean;
    lowestBidValue: number;
    compStep: number;
  }>>({});

  // Synchronize active bidding states back to bundleStates map
  useEffect(() => {
    if (!selectedBundle) return;
    setBundleStates(prev => {
      const current = prev[selectedBundle.id];
      if (
        current &&
        current.driverBid === driverBid &&
        current.bidsFeed === bidsFeed &&
        current.biddingActive === biddingActive &&
        current.isLowest === isLowest &&
        current.lowestBidValue === lowestBidValue &&
        current.compStep === compStep
      ) {
        return prev;
      }
      return {
        ...prev,
        [selectedBundle.id]: {
          driverBid,
          bidsFeed,
          biddingActive,
          isLowest,
          lowestBidValue,
          compStep
        }
      };
    });
  }, [selectedBundle?.id, driverBid, bidsFeed, biddingActive, isLowest, lowestBidValue, compStep]);

  // Helper to switch or select a bundle
  const selectBundle = (bundle: any) => {
    if (selectedBundle?.id === bundle.id) return;

    if (compTimerRef.current) {
      clearTimeout(compTimerRef.current);
      compTimerRef.current = null;
    }

    const nextState = bundleStates[bundle.id] || {
      driverBid: "",
      bidsFeed: [],
      biddingActive: false,
      isLowest: true,
      lowestBidValue: Infinity,
      compStep: 0
    };

    setDriverBid(nextState.driverBid);
    setBidsFeed(nextState.bidsFeed);
    setBiddingActive(nextState.biddingActive);
    setIsLowest(nextState.isLowest);
    setLowestBidValue(nextState.lowestBidValue);
    setCompStep(nextState.compStep);
    setSelectedBundle(bundle);
  };

  // Helper to close a bid details panel
  const handleCloseBid = () => {
    if (compTimerRef.current) {
      clearTimeout(compTimerRef.current);
      compTimerRef.current = null;
    }

    setSelectedBundle(null);
    setDriverBid("");
    setBidsFeed([]);
    setBiddingActive(false);
    setIsLowest(true);
    setLowestBidValue(Infinity);
    setCompStep(0);
  };

  // Winner Modal states
  const [showWinModal, setShowWinModal] = useState(false);
  const [winContractValue, setWinContractValue] = useState(0);
  const [wonBundle, setWonBundle] = useState<any>(null);

  // Notifications State
  const [notifications, setNotifications] = useState<any[]>([
    {
      title: "New Load Available",
      message: "Bundle #KB1024 ready for cooperative logistics bidding.",
      time: "Just Now",
      read: false,
      type: "new_load"
    }
  ]);

  const getNotificationStyle = (type: string) => {
    switch (type) {
      case "contract_won":
        return {
          containerClass: "border-l-4 border-l-field border-field/30 bg-[#f7fbf7] hover:bg-[#eff7ef] shadow-sm",
          titleClass: "text-field font-black",
          badgeColor: "bg-field",
          icon: "🎉"
        };
      case "bid":
        return {
          containerClass: "border-l-4 border-l-harvest border-harvest/30 bg-[#fffcf5] hover:bg-[#fff7e6] shadow-sm",
          titleClass: "text-[#d67d00] font-bold",
          badgeColor: "bg-harvest",
          icon: "⚡"
        };
      case "new_load":
        return {
          containerClass: "border-l-4 border-l-river border-river/30 bg-[#f4f8fc] hover:bg-[#e8f1f8] shadow-sm",
          titleClass: "text-river font-bold",
          badgeColor: "bg-river",
          icon: "📦"
        };
      default:
        return {
          containerClass: "border-l-4 border-l-stone-400 border-stone-200 bg-stone-50 hover:bg-stone-100/85 shadow-sm",
          titleClass: "text-stone-850 font-bold",
          badgeColor: "bg-stone-400",
          icon: "🔔"
        };
    }
  };

  const handleNotificationClick = (notif: any) => {
    // Mark as read
    setNotifications(prev =>
      prev.map(n => (n === notif ? { ...n, read: true } : n))
    );

    const msg = notif.message || "";
    const bundleMatch = msg.match(/KB-?\d+/i);
    
    if (notif.type === "contract_won" || notif.type === "trip_update" || msg.toLowerCase().includes("trip") || msg.toLowerCase().includes("journey") || msg.toLowerCase().includes("assigned")) {
      router.push("/driver/trip");
    } else if (bundleMatch) {
      const bId = bundleMatch[0].replace("-", "").toUpperCase();
      const target = bundles.find(b => b.id.toUpperCase().replace("-", "") === bId);
      if (target) {
        selectBundle(target);
      }
    } else if (msg.toLowerCase().includes("savings") || msg.toLowerCase().includes("analytics") || msg.toLowerCase().includes("payout")) {
      const targetEl = document.getElementById("performance-metrics");
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  // Check if driver has already won any bid (on page load + periodic)
  useEffect(() => {
    if (!user) return;
    const checkWon = async () => {
      const { data } = await supabase
        .from("bids")
        .select("id, bundle_id, amount, status")
        .eq("driver_name", user.name)
        .eq("status", "Accepted")
        .limit(1);
      if (data && data.length > 0) {
        const winBid = data[0];
        setWonBundle(winBid);
        setWinContractValue(winBid.amount);
      }
    };
    checkWon();
    const interval = setInterval(checkWon, 10000);
    return () => clearInterval(interval);
  }, [user]);

  // Load bundles
  useEffect(() => {
    async function getBundles() {      if (!user) return;
      try {
        const { data } = await supabase.from("bundles").select("*").order("created_at", { ascending: false });
        if (data && data.length > 0) {
          // For each bundle, fetch real orders to get crops and distance
          const enriched = await Promise.all(data.map(async (b) => {
            let cropLabel = "Mixed Produce";
            let distanceKm = 0;

            // Get orders linked to this bundle via cluster_id (same as bundle id)
            const { data: orders } = await supabase
              .from("orders")
              .select("id, farmer_name, phone, crop, weight_kg, village, lat, lng, individual_cost, shared_cost")
              .eq("cluster_id", b.id);

            if (orders && orders.length > 0) {
              // Build crop summary e.g. "Tomato (400kg), Brinjal (250kg)"
              const cropMap: Record<string, number> = {};
              orders.forEach((o: any) => {
                cropMap[o.crop] = (cropMap[o.crop] || 0) + o.weight_kg;
              });
              cropLabel = Object.entries(cropMap)
                .map(([crop, kg]) => `${crop} (${kg}kg)`)
                .join(", ");

              // Distance: use average route_leg_km if available (from OR-Tools), else haversine
              const mandiLat = 13.0716;
              const mandiLng = 80.1945;
              const hasRouteData = orders.some((o: any) => o.route_leg_km && o.route_leg_km > 0);
              if (hasRouteData) {
                const totalLegs = orders.reduce((s: number, o: any) => s + (o.route_leg_km || 0), 0);
                distanceKm = Math.round(totalLegs);
              } else {
                const geoOrders = orders.filter((o: any) => o.lat && o.lng);
                if (geoOrders.length > 0) {
                  const avgDist = geoOrders.reduce((sum: number, o: any) => {
                    const dLat = (o.lat - mandiLat) * Math.PI / 180;
                    const dLng = (o.lng - mandiLng) * Math.PI / 180;
                    const a = Math.sin(dLat / 2) ** 2 +
                      Math.cos(o.lat * Math.PI / 180) * Math.cos(mandiLat * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
                    return sum + 6371 * 2 * Math.asin(Math.sqrt(a));
                  }, 0) / geoOrders.length;
                  distanceKm = Math.round(avgDist);
                }
              }
            }

            // Get shared costs for earnings (driver earns sum of farmer shared costs)
            const { data: sharedOrders } = await supabase
              .from("orders")
              .select("shared_cost")
              .eq("cluster_id", b.id);
            const earnings = sharedOrders
              ? sharedOrders.reduce((s: number, o: any) => s + (o.shared_cost || 0), 0)
              : Math.round(b.estimated_savings * 1.5);

            // Fallback distance if no GPS data
            if (distanceKm === 0) distanceKm = Math.round(b.total_weight_kg / 50 + 60);

            // Driver trip cost using real fuel and wage rates per vehicle class
            const tripCost = calculateDriverTripCost(distanceKm, b.total_weight_kg);

            return {
              id: b.id,
              pickup: "Farmer Collection Points",
              destination: b.destination,
              weight: b.total_weight_kg,
              crop: cropLabel,
              earnings: earnings || Math.round(b.estimated_savings * 1.5),
              distance: distanceKm,
              fuel: tripCost.fuelCost,
              driverWage: tripCost.driverWage,
              totalDriverCost: tripCost.totalDriverCost,
              suggestedBidMin: tripCost.suggestedBidMin,
              suggestedBidMax: tripCost.suggestedBidMax,
              vehicleClass: tripCost.vehicleClass,
              orders: orders || []
            };
          }));

          setBundles(enriched);
        } else {
          // Fallback mockup
          setBundles([
            {
              id: "KB1024",
              pickup: "Melma Farmers Pool",
              destination: "Koyambedu Mandi",
              weight: 1200,
              crop: "Tomato (900kg), Brinjal (300kg)",
              earnings: 4200,
              distance: 72,
              fuel: 580
            }
          ]);
        }
      } catch (err) {
        console.error(err);
      }
    }
    getBundles();
  }, [user]);

  // Handle bidding submission
  const submitBid = async () => {
    const amount = Number(driverBid);
    if (!amount || amount <= 0) {
      alert("Please enter a valid bid amount");
      return;
    }

    console.log("🚀 Submitting bid:", {
      bundle_id: selectedBundle.id,
      driver_name: user.name,
      amount: amount
    });

    // Store in Supabase bids table
    try {
      // Check if bidding is closed for this bundle
      const { data: closedCheck } = await supabase
        .from("bids")
        .select("status")
        .eq("bundle_id", selectedBundle.id)
        .in("status", ["Accepted", "Closed"])
        .limit(1);

      if (closedCheck && closedCheck.length > 0) {
        alert("Bidding is closed for this cluster. A winner has already been selected.");
        return;
      }

      // First, check if this driver already has a bid on this cluster
      const { data: existingBids, error: checkError } = await supabase
        .from("bids")
        .select("id, amount")
        .eq("bundle_id", selectedBundle.id)
        .eq("driver_name", user.name);

      if (checkError) {
        console.error("❌ Error checking existing bids:", checkError);
      }

      // If driver already has a bid, check if new bid is lower
      if (existingBids && existingBids.length > 0) {
        const currentBid = existingBids[0];
        
        // Check if new bid is lower than driver's current bid
        if (amount >= currentBid.amount) {
          alert(`You already have a bid of ₹${currentBid.amount}. New bid must be lower than your current bid to update it.`);
          return;
        }

        // Check if new bid is lower than current lowest from other drivers
        const { data: allBids } = await supabase
          .from("bids")
          .select("amount, driver_name")
          .eq("bundle_id", selectedBundle.id)
          .neq("driver_name", user.name)
          .order("amount", { ascending: true });

        if (allBids && allBids.length > 0) {
          const lowestOtherBid = allBids[0].amount;
          if (amount >= lowestOtherBid) {
            alert(`Your new bid (₹${amount}) must be lower than the current lowest bid (₹${lowestOtherBid}) from ${allBids[0].driver_name}.`);
            return;
          }
        }

        // Update existing bid instead of creating new one
        const { data: updateData, error: updateError } = await supabase
          .from("bids")
          .update({ amount: amount })
          .eq("id", currentBid.id)
          .select();

        if (updateError) {
          console.error("❌ Error updating bid:", updateError);
          alert("Failed to update bid. Please try again.");
          return;
        }

        console.log("✅ Bid updated successfully:", updateData);
        alert(`Bid updated successfully! New amount: ₹${amount}`);

      } else {
        // No existing bid, create new one
        const { data, error } = await supabase.from("bids").insert({
          id: `BID-${Date.now()}`,
          bundle_id: selectedBundle.id,
          driver_id: user.driverId || user.id,
          driver_name: user.name,
          vehicle: "Mini Truck",
          amount: amount,
          reliability_score: user.reliability_score || 94,
          bid_type: "cluster",  // Mark as cluster bid
          status: "Open"
        }).select();

        if (error) {
          console.error("❌ Error inserting bid:", error);
          alert("Failed to submit bid. Please try again.");
          return;
        }

        console.log("✅ Bid inserted successfully:", data);
        alert(`Bid submitted successfully! Amount: ₹${amount}`);
      }

      // Refresh bids from database to get latest state
      const { data: allBids } = await supabase
        .from("bids")
        .select("driver_name, vehicle, amount, reliability_score, created_at, status")
        .eq("bundle_id", selectedBundle.id)
        .order("created_at", { ascending: false });

      if (allBids && allBids.length > 0) {
        const formattedBids: BidEvent[] = allBids.map((bid: any) => ({
          driverName: bid.driver_name,
          vehicle: bid.vehicle || "Mini Truck",
          amount: bid.amount,
          reliability: bid.reliability_score || 94,
          timestamp: new Date(bid.created_at).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          })
        }));

        setBidsFeed(formattedBids);

        // Calculate lowest bid
        const amounts = allBids.map((b: any) => b.amount);
        const minBid = Math.min(...amounts);
        setLowestBidValue(minBid);

        // Check if current driver's bid is lowest
        const myBid = allBids.find((b: any) => b.driver_name === user.name);
        if (myBid) {
          setIsLowest(myBid.amount <= minBid);
        }
      }

      setBiddingActive(true);

      // Show success notification
      setNotifications(prev => [
        {
          title: "✅ Bid Submitted",
          message: `Your bid of ₹${amount} has been placed on Bundle #${selectedBundle.id}`,
          time: "Just Now",
          read: false,
          type: "bid"
        },
        ...prev
      ]);
      
    } catch (e) {
      console.error("❌ Error submitting bid:", e);
      alert("An error occurred. Please try again.");
    }
  };

  // Fetch real bids from database when bundle is selected
  useEffect(() => {
    if (!selectedBundle) return;

    const fetchRealBids = async () => {
      try {
        console.log("🔍 Fetching bids for cluster:", selectedBundle.id);
        
        const { data: bids, error } = await supabase
          .from("bids")
          .select("driver_name, vehicle, amount, reliability_score, created_at, status")
          .eq("bundle_id", selectedBundle.id)
          .order("created_at", { ascending: false });

        if (error) {
          console.error("❌ Error fetching bids:", error);
          return;
        }

        console.log("📊 Fetched bids:", bids);

        if (bids && bids.length > 0) {
          const formattedBids: BidEvent[] = bids.map((bid: any) => ({
            driverName: bid.driver_name,
            vehicle: bid.vehicle || "Standard Truck",
            amount: bid.amount,
            reliability: bid.reliability_score || 90,
            timestamp: new Date(bid.created_at).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit', 
              second: '2-digit' 
            })
          }));

          console.log("✅ Formatted bids:", formattedBids);
          setBidsFeed(formattedBids);

          // Calculate lowest bid
          const amounts = bids.map((b: any) => b.amount);
          const minBid = Math.min(...amounts);
          setLowestBidValue(minBid);

          // Check if current driver's bid is lowest
          const driverAmount = Number(driverBid);
          if (driverAmount > 0) {
            setIsLowest(driverAmount <= minBid);
          }

          // Check if driver won (bid marked Accepted by admin closing)
          const myBidStatus = bids.find((b: any) => b.driver_name === user?.name);
          if (myBidStatus?.status === "Accepted" && !wonBundle) {
            setWonBundle({ bundle_id: selectedBundle.id, amount: myBidStatus.amount });
            setWinContractValue(myBidStatus.amount);
            setNotifications(prev => [
              {
                title: "🏆 Contract Won!",
                message: `You won Bundle #${selectedBundle.id} for ₹${myBidStatus.amount}. Go to Active Journey Map.`,
                time: "Just Now",
                read: false,
                type: "contract_won"
              },
              ...prev
            ]);
          }
        } else {          console.log("⚠️ No bids found for cluster:", selectedBundle.id);
          setBidsFeed([]); // Clear feed if no bids
        }
      } catch (err) {
        console.error("❌ Error in fetchRealBids:", err);
      }
    };

    fetchRealBids();

    // Refresh bids every 10 seconds to show new bids from other drivers
    const interval = setInterval(fetchRealBids, 10000);

    return () => {
      clearInterval(interval);
      if (compTimerRef.current) {
        clearTimeout(compTimerRef.current);
        compTimerRef.current = null;
      }
    };
  }, [selectedBundle?.id, driverBid]);

  const handleLogout = async () => {
    localStorage.removeItem("kb_demo_session");
    await supabase.auth.signOut();
    router.push("/login");
  };

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
      {/* Side Navigation panel */}
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
            <Link href="/driver/loads" className="flex items-center gap-2.5 bg-soil/5 text-soil p-2.5 rounded-lg border border-soil/10">
              <Compass size={17} /> Available Loads
            </Link>
            <Link href="/driver/trip" className="flex items-center gap-2.5 hover:bg-stone-50 p-2.5 rounded-lg hover:text-soil transition-all">
              <MapPin size={17} /> Active Journey Map
            </Link>
          </nav>

          {/* Performance & Score panel - Removed as requested */}
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
            <h1 className="text-2xl font-black text-soil uppercase tracking-wide">Available Loads</h1>
            <p className="text-xs text-stone-500">Bid on clustered farmer loads. Individual order bidding is disabled.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('bundles')}
                className={`rounded-lg px-4 py-2 text-sm font-bold transition-all ${
                  viewMode === 'bundles'
                    ? 'bg-field text-white'
                    : 'bg-white border border-stone-300 text-stone-600 hover:bg-stone-50'
                }`}
              >
                📦 Clusters
              </button>
              <button
                onClick={() => setViewMode('trips')}
                className={`rounded-lg px-4 py-2 text-sm font-bold transition-all ${
                  viewMode === 'trips'
                    ? 'bg-field text-white'
                    : 'bg-white border border-stone-300 text-stone-600 hover:bg-stone-50'
                }`}
              >
                🚛 My Trips
              </button>
            </div>
            <span className="text-xs font-semibold text-stone-500">Welcome, {user.name}</span>
          </div>
        </div>

        {/* Win Banner */}
        {wonBundle && (
          <div className="rounded-xl border-2 border-field bg-field/5 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fadeIn">
            <div className="flex items-center gap-3">
              <CheckCircle className="text-field flex-shrink-0" size={28} />
              <div>
                <p className="text-sm font-black text-field uppercase tracking-wide">🎉 You Won the Bid!</p>
                <p className="text-xs text-stone-600 mt-0.5">
                  Bundle <strong>#{wonBundle.bundle_id}</strong> assigned to you for <strong>₹{wonBundle.amount.toLocaleString("en-IN")}</strong>
                </p>
              </div>
            </div>
            <Link
              href="/driver/trip"
              className="flex-shrink-0 bg-field text-white px-5 py-2 text-xs font-black rounded-lg hover:bg-field/90 transition-all uppercase tracking-wider"
            >
              View Active Trip →
            </Link>
          </div>
        )}

        {/* My Trips View - Active and Past Trips */}
        {viewMode === 'trips' && (
          <DriverTripsView user={user} />
        )}

        {/* Bundle View */}
        {viewMode === 'bundles' && (
        <div className="space-y-6">
          {/* Cluster Cards Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {bundles.length === 0 ? (
              <p className="text-sm text-stone-400 italic col-span-full">No available loads in your area.</p>
            ) : (
              bundles.map((bundle) => (
                <div
                  key={bundle.id}
                  onClick={() => selectBundle(bundle)}
                  className={`rounded-xl border p-5 shadow-panel cursor-pointer transition-all bg-white relative overflow-hidden ${
                    selectedBundle?.id === bundle.id 
                      ? "border-soil ring-2 ring-soil bg-soil/5" 
                      : "border-stone-200 hover:border-soil/40 hover:shadow-lg"
                  }`}
                >
                  <div className="absolute top-0 right-0 bg-soil/10 text-soil font-black text-[10px] px-3 py-1 rounded-bl-lg uppercase">
                    Bundle #{bundle.id}
                  </div>
                  
                  <div className="space-y-3 mt-4">
                    <div className="flex justify-between items-center">
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold rounded bg-river/10 text-river px-2.5 py-0.5">
                        <MapPin size={11} /> {bundle.destination}
                      </span>
                    </div>

                    <div className="space-y-2 text-xs text-stone-600">
                      <div className="flex items-center gap-2">
                        <Scale size={14} className="text-stone-400" />
                        <span>Weight: <strong className="text-stone-800">{bundle.weight} kg</strong></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Sprout size={14} className="text-stone-400" />
                        <span>Crop: <strong className="text-stone-800">{bundle.crop.split('(')[0]}</strong></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Compass size={14} className="text-stone-400" />
                        <span>Distance: <strong className="text-stone-800">{bundle.distance} km</strong></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <IndianRupee size={14} className="text-stone-400" />
                        <span>Farmer Pool: <strong className="text-field font-black">₹{bundle.earnings}</strong></span>
                      </div>
                    </div>
                    
                    {selectedBundle?.id === bundle.id && (
                      <div className="mt-3 pt-3 border-t border-stone-200">
                        <p className="text-xs text-soil font-bold animate-pulse">
                          ✓ Selected - Scroll down to place bid
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Bidding Interface Section - Shows when cluster selected */}
          {selectedBundle && (
            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              {/* Bidding Form */}
              <section className="rounded-xl border-2 border-soil bg-white p-6 shadow-lg space-y-4 animate-fadeIn">
                <div className="flex justify-between items-center border-b border-stone-100 pb-3">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-black text-soil uppercase tracking-wider">
                      📝 Place Bid for Bundle #{selectedBundle.id}
                    </h3>
                  </div>
                  <button
                    type="button"
                    onClick={handleCloseBid}
                    className="text-stone-400 hover:text-stone-600 hover:bg-stone-50 p-2 rounded-full border border-stone-200 transition-colors flex items-center justify-center"
                    title="Close bid panel"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Cluster Summary */}
                <div className="bg-stone-50 rounded-lg p-4 space-y-2 text-sm">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-stone-500">Weight:</span>
                      <p className="font-bold text-stone-800">{selectedBundle.weight} kg</p>
                    </div>
                    <div>
                      <span className="text-stone-500">Distance:</span>
                      <p className="font-bold text-stone-800">{selectedBundle.distance} km</p>
                    </div>
                    <div>
                      <span className="text-stone-500">Farmer Payout Pool:</span>
                      <p className="font-bold text-field">₹{selectedBundle.earnings}</p>
                    </div>
                    <div>
                      <span className="text-stone-500">Vehicle Class:</span>
                      <p className="font-bold text-stone-800 capitalize">{selectedBundle.vehicleClass || "standard"} truck</p>
                    </div>
                  </div>

                </div>

                {/* Farmers List */}
                {selectedBundle.orders && selectedBundle.orders.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-black text-soil uppercase tracking-wider">
                        📋 Farmers in This Cluster ({selectedBundle.orders.length} Orders)
                      </h4>
                    </div>
                    
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
                      {selectedBundle.orders.map((order: any, idx: number) => (
                        <div 
                          key={order.id || idx} 
                          className="bg-white border border-stone-200 rounded-lg p-3 hover:border-soil/40 transition-all"
                        >
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-soil/10 text-soil text-xs font-bold">
                                  {idx + 1}
                                </span>
                                <span className="font-bold text-stone-800 text-sm">
                                  {order.farmer_name || 'Farmer ' + (idx + 1)}
                                </span>
                              </div>
                              <p className="text-xs text-stone-500 ml-8">
                                📞 {order.phone || 'N/A'}
                              </p>
                            </div>
                            <span className="text-xs font-bold text-field">
                              ₹{order.shared_cost || order.individual_cost || 0}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-2 text-xs text-stone-600 ml-8">
                            <div className="flex items-center gap-1.5">
                              <Sprout size={12} className="text-stone-400" />
                              <span><strong>{order.crop}</strong> • {order.weight_kg}kg</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <MapPin size={12} className="text-stone-400" />
                              <span className="truncate" title={order.village}>
                                {order.village?.split(',')[0] || 'Location'}
                              </span>
                            </div>
                          </div>
                          
                          {order.village && (
                            <div className="mt-2 pt-2 border-t border-stone-100">
                              <p className="text-xs text-stone-500">
                                <strong>Pickup:</strong> {order.village}
                              </p>
                              <p className="text-xs text-stone-500 mt-1">
                                <strong>Destination:</strong> {selectedBundle.destination}
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                    
                    <div className="bg-river/5 border border-river/20 rounded-lg p-3 text-xs">
                      <p className="text-stone-700">
                        <strong className="text-river">💡 Route Plan:</strong> Pickup all {selectedBundle.orders.length} orders from their respective locations, 
                        then deliver to {selectedBundle.destination}. Total distance: ~{selectedBundle.distance}km
                      </p>
                    </div>
                  </div>
                )}

                {/* Bid Input */}
                <div className="space-y-3">
                  <label className="block text-sm font-bold text-stone-700">
                    Your Bid Amount
                  </label>
                  <div className="flex gap-3">
                    <div className="relative flex-1">
                      <span className="absolute left-4 top-3.5 text-stone-400 font-bold text-base">₹</span>
                      <input
                        type="number"
                        placeholder="Enter bid amount (e.g. 4000)"
                        value={driverBid}
                        disabled={biddingActive}
                        onChange={(e) => setDriverBid(e.target.value)}
                        className="focus-ring w-full rounded-lg border-2 border-stone-300 pl-9 pr-4 py-3 text-base font-semibold text-stone-800 focus:border-soil"
                      />
                    </div>
                    <button
                      onClick={submitBid}
                      disabled={biddingActive || !driverBid}
                      className="focus-ring bg-soil text-white px-8 py-3 text-base font-bold rounded-lg hover:bg-soil/95 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                    >
                      {biddingActive ? '⏳ Bidding...' : '🚀 Submit Bid'}
                    </button>
                  </div>
                </div>

                {/* Status Indicator */}
                {bidsFeed.length > 0 && (
                  <div className="mt-4 flex items-center justify-between p-4 rounded-lg border-2 text-sm bg-stone-50">
                    <span className="font-bold text-stone-700">My Bid Status:</span>
                    {isLowest ? (
                      <span className="inline-flex items-center gap-2 font-black text-field bg-field/10 border-2 border-field/20 px-4 py-2 rounded-full uppercase tracking-wider">
                        🟢 Lowest Bid - You are leading!
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-2 font-black text-chilli bg-chilli/10 border-2 border-chilli/20 px-4 py-2 rounded-full uppercase tracking-wider animate-pulse">
                        ❌ Outbid - Place Lower Bid
                      </span>
                    )}
                  </div>
                )}
              </section>

              {/* Live Bid Feed & Notifications */}
              <div className="space-y-4">
                {/* Live Bid Feed */}
                {bidsFeed.length > 0 && (
                  <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-panel space-y-3">
                    <h3 className="text-xs font-black text-soil uppercase tracking-wider flex items-center gap-1.5">
                      <Clock size={14} className="text-soil animate-spin-slow" />
                      Live Competitor Bids
                    </h3>
                    
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                      {bidsFeed.map((bid, i) => (
                        <div key={i} className="rounded-lg border border-stone-100 p-3 bg-stone-50 flex justify-between items-center text-xs animate-fadeIn">
                          <div>
                            <div className="flex items-center gap-1">
                              <span className="font-bold text-stone-800">{bid.driverName}</span>
                              <span className="text-[10px] text-stone-400 font-mono">({bid.vehicle})</span>
                            </div>
                            <span className="text-[9px] text-stone-400">{bid.timestamp}</span>
                          </div>
                          <div className="text-right">
                            <p className="font-black text-soil">₹{bid.amount}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Notification Center */}
                <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-panel space-y-4">
                  <h3 className="text-xs font-black text-soil uppercase tracking-wider flex items-center gap-1.5">
                    <Bell size={15} className="text-soil" />
                    Notifications
                  </h3>

                  <div className="space-y-2.5 max-h-[400px] overflow-y-auto pr-1 text-left">
                    {notifications.slice(0, 5).map((notif, index) => {
                      const style = getNotificationStyle(notif.type || "");
                      return (
                        <div 
                          key={index} 
                          onClick={() => handleNotificationClick(notif)}
                          className={`group rounded-lg p-3 cursor-pointer transition-all relative select-none active:scale-[0.98] ${style.containerClass} ${!notif.read ? "ring-1 ring-soil/15" : "opacity-80"}`}
                        >
                          <div className="flex justify-between items-start gap-1">
                            <strong className={`text-xs ${style.titleClass} flex items-center gap-1.5`}>
                              <span>{style.icon}</span>
                              {notif.title}
                            </strong>
                            <span className="text-[9px] text-stone-400 font-mono flex-shrink-0">{notif.time}</span>
                          </div>
                          <p className="text-[11px] text-stone-700 mt-1 leading-relaxed">{notif.message}</p>
                        </div>
                      );
                    })}
                  </div>
                </section>
              </div>
            </div>
          )}
        </div>
        )}
      </section>

      {/* FEATURE 2: Winner Celebration Modal */}
      {showWinModal && (
        <>
          <style jsx>{`
            .modal-btn-primary {
              background-color: #15803d !important;
              color: white !important;
            }
            .modal-btn-primary:hover {
              background-color: #166534 !important;
            }
            .modal-btn-secondary {
              background-color: #1f2937 !important;
              color: white !important;
            }
            .modal-btn-secondary:hover {
              background-color: #111827 !important;
            }
          `}</style>
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-2xl border-2 border-soil bg-white p-6 shadow-2xl relative overflow-hidden text-center animate-fadeIn">
            {/* Background Confetti Pattern */}
            <div className="absolute inset-0 bg-gradient-to-b from-soil/5 to-white pointer-events-none" />
            
            <CheckCircle className="mx-auto text-field mb-3 animate-bounce" size={44} />
            <h3 className="text-xl font-black text-soil uppercase tracking-wide">🎉 CONGRATULATIONS</h3>
            <p className="text-sm font-bold text-stone-700 mt-1">You Won The Cooperative Contract</p>
            
            <div className="mt-5 rounded-xl bg-stone-50 border border-stone-150 p-4 space-y-2 text-xs font-mono text-left max-w-xs mx-auto">
              <div className="flex justify-between">
                <span className="text-stone-400">Bundle ID:</span>
                <strong className="text-stone-800">#{selectedBundle?.id}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-400">Contract Value:</span>
                <strong className="text-field font-black">₹{winContractValue}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-400">Pickup Time:</span>
                <strong className="text-stone-800">Tomorrow 7:00 AM</strong>
              </div>
            </div>

            <div className="mt-6 flex flex-col gap-3">
              <button
                onClick={() => {
                  setShowWinModal(false);
                  router.push("/driver/trip");
                }}
                className="modal-btn-primary w-full py-4 px-4 text-base font-black rounded-xl transition-all shadow-lg"
              >
                GO TO ACTIVE TRIP
              </button>
              <button
                onClick={() => setShowWinModal(false)}
                className="modal-btn-secondary w-full py-4 px-4 text-base font-bold rounded-xl transition-all shadow-lg"
              >
                DISMISS
              </button>
            </div>
          </div>
        </div>
        </>
      )}
    </main>
  );
}
