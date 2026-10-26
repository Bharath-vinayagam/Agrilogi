"use client";

import { BadgeIndianRupee, ClipboardCheck, Send, Truck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/services/api";
import { supabase } from "@/services/supabase";
import type { Bid, Driver, FarmerOrder } from "@/types";
import { StatusPill } from "@/components/StatusPill";

export function DriverDashboard() {
  const [bids, setBids] = useState<Bid[]>([]);
  const [orders, setOrders] = useState<FarmerOrder[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  // Registration form refs
  const nameRef = useRef<HTMLInputElement>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const vehicleNumberRef = useRef<HTMLInputElement>(null);
  const licenseRef = useRef<HTMLInputElement>(null);
  const vehicleTypeRef = useRef<HTMLSelectElement>(null);

  async function loadData() {
    try {
      const [fetchedBids, fetchedOrders, fetchedDrivers] = await Promise.all([
        api.getBids(),
        api.getOrders(),
        api.getDrivers()
      ]);
      setBids(fetchedBids);
      setOrders(fetchedOrders);
      setDrivers(fetchedDrivers);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleSaveVehicle() {
    const name = nameRef.current?.value.trim();
    const phone = phoneRef.current?.value.trim();
    const vehicleNumber = vehicleNumberRef.current?.value.trim();
    const licenseNumber = licenseRef.current?.value.trim();
    const vehicleType = vehicleTypeRef.current?.value ?? "Mini Truck";

    if (!name || !phone || !vehicleNumber || !licenseNumber) {
      alert("Please fill in all fields before saving.");
      return;
    }

    setSaveStatus("saving");
    try {
      const digitsOnly = phone.replace(/\D/g, "").slice(-10);
      const email = `user${digitsOnly}@myapp.com`;

      // Check if user already exists
      const { data: existing } = await supabase
        .from("users")
        .select("id")
        .eq("phone", phone)
        .maybeSingle();

      let userId: string;

      if (existing) {
        userId = existing.id;
      } else {
        // Create Supabase auth + users row
        const { data: authData, error: authErr } = await supabase.auth.signUp({
          email,
          password: digitsOnly,
        });
        if (authErr || !authData.user) throw new Error(authErr?.message ?? "Auth signup failed");
        userId = authData.user.id;

        await supabase.from("users").insert({
          id: userId,
          name,
          phone,
          role: "driver",
          preferred_language: "en",
        });
      }

      // Determine capacity from vehicle type
      const vLower = vehicleType.toLowerCase();
      let capacityKg = 1100;
      if (vLower.includes("mini") || vLower.includes("ace")) capacityKg = 500;
      else if (vLower.includes("heavy") || vLower.includes("leyland")) capacityKg = 2500;

      // Insert driver profile
      const { data: driverRow, error: driverErr } = await supabase
        .from("drivers")
        .insert({
          user_id: userId,
          vehicle_number: vehicleNumber,
          vehicle_type: vehicleType,
          license_number: licenseNumber,
          reliability_score: 94,
          completed_trips: 0,
          rating: 4.8,
        })
        .select()
        .single();

      if (driverErr) throw new Error(driverErr.message);

      // Insert vehicle capacity record
      await supabase.from("vehicles").insert({
        driver_id: driverRow.id,
        vehicle_number: vehicleNumber,
        vehicle_type: vehicleType,
        capacity_kg: capacityKg,
      });

      setSaveStatus("saved");
      loadData();
      // Clear form
      if (nameRef.current) nameRef.current.value = "";
      if (phoneRef.current) phoneRef.current.value = "";
      if (vehicleNumberRef.current) vehicleNumberRef.current.value = "";
      if (licenseRef.current) licenseRef.current.value = "";
    } catch (err: any) {
      console.error("Save vehicle error:", err);
      setSaveStatus("error");
    }
  }

  async function submitBid(formData: FormData) {
    const amount = Number(formData.get("bid") || 4500);
    const payload = {
      driver_name: "Your Vehicle",
      vehicle: "Mini Truck",
      amount,
      reliability_score: 90
    };

    try {
      const newBid = await api.submitBid(payload);
      if (newBid) {
        setBids([newBid, ...bids]);
      }
    } catch (err) {
      console.error(err);
    }
  }

  const totalWeight = orders.reduce((sum, order) => sum + order.weightKg, 0);

  return (
    <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-soil">Driver Registration</h2>
          <Truck className="text-field" size={24} />
        </div>
        <div className="mt-4 grid gap-3">
          <input ref={nameRef} className="focus-ring rounded-lg border border-stone-300 px-3 py-2" placeholder="Name" />
          <input ref={phoneRef} className="focus-ring rounded-lg border border-stone-300 px-3 py-2" placeholder="Phone Number" type="tel" />
          <input ref={vehicleNumberRef} className="focus-ring rounded-lg border border-stone-300 px-3 py-2" placeholder="Vehicle Number" />
          <input ref={licenseRef} className="focus-ring rounded-lg border border-stone-300 px-3 py-2" placeholder="Driving License Number" />
          <select ref={vehicleTypeRef} className="focus-ring rounded-lg border border-stone-300 px-3 py-2" defaultValue="Tata Ace">
            {["Tata Ace", "Mahindra Bolero Pickup", "Ashok Leyland Dost", "Mini Truck", "Other"].map((vehicle) => (
              <option key={vehicle}>{vehicle}</option>
            ))}
          </select>
          <button
            className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg bg-field px-4 py-2 font-semibold text-white disabled:opacity-60"
            type="button"
            disabled={saveStatus === "saving"}
            onClick={handleSaveVehicle}
          >
            <ClipboardCheck size={18} />
            {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved ✓" : saveStatus === "error" ? "Error — retry" : "Save Vehicle"}
          </button>
        </div>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel">
        <h2 className="text-lg font-bold text-soil">Available Load</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-5">
          <div className="rounded-lg bg-stone-50 p-3">
            <p className="text-xs text-stone-500">Pickup Villages</p>
            <p className="font-bold">Melma, Athur, Sevoor</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-3">
            <p className="text-xs text-stone-500">Destination</p>
            <p className="font-bold">Koyambedu</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-3">
            <p className="text-xs text-stone-500">Total Weight</p>
            <p className="font-bold">{totalWeight} kg</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-3">
            <p className="text-xs text-stone-500">Expected Earnings</p>
            <p className="font-bold">Rs 4,350</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-3">
            <p className="text-xs text-stone-500">Crops</p>
            <p className="font-bold">Tomato, Brinjal</p>
          </div>
        </div>

        <form action={submitBid} className="mt-4 flex flex-wrap gap-3">
          <label className="flex min-w-64 flex-1 items-center gap-2 rounded-lg border border-stone-300 px-3 py-2">
            <BadgeIndianRupee size={18} />
            <input className="w-full outline-none" min="1" name="bid" placeholder="Driver Bid" type="number" required />
          </label>
          <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-soil px-4 py-2 font-semibold text-white" type="submit">
            <Send size={18} />
            Submit Bid
          </button>
        </form>

        <div className="mt-4 overflow-x-auto">
          {loading ? (
            <p className="text-sm text-stone-500">Loading bids...</p>
          ) : (
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="text-stone-500">
                <tr>
                  <th className="py-2">Driver</th>
                  <th>Vehicle</th>
                  <th>Bid Amount</th>
                  <th>Reliability</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {bids.map((bid) => (
                  <tr className="border-t border-stone-200" key={bid.id}>
                    <td className="py-3 font-semibold">{bid.driverName}</td>
                    <td>{bid.vehicle}</td>
                    <td>Rs {bid.amount.toLocaleString("en-IN")}</td>
                    <td>{bid.reliabilityScore}%</td>
                    <td>
                      <StatusPill status={bid.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-panel xl:col-span-2">
        <h2 className="text-lg font-bold text-soil">Active Trips</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {drivers.map((driver) => (
            <div className="rounded-lg border border-stone-200 p-4" key={driver.id}>
              <p className="font-bold text-soil">{driver.name}</p>
              <p className="mt-1 text-sm text-stone-600">{driver.vehicleType} / {driver.vehicleNumber}</p>
              <div className="mt-4 flex gap-3">
                <button className="focus-ring rounded-lg border border-stone-300 px-4 py-2 text-sm font-semibold">Picked Up</button>
                <button className="focus-ring rounded-lg bg-field px-4 py-2 text-sm font-semibold text-white">Delivered</button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

