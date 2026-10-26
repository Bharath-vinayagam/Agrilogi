"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/services/supabase";
import { sendRegistrationSMS } from "@/services/sms";
import { Languages, AlertCircle, ArrowLeft, CheckCircle2 } from "lucide-react";
import Link from "next/link";

export default function RegisterPage() {
  const [step, setStep] = useState(1);
  const [role, setRole] = useState<"farmer" | "driver" | null>(null);

  // Common Fields
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Farmer Fields
  const [village, setVillage] = useState("");
  const [preferredLanguage, setPreferredLanguage] = useState("ta");

  // Driver Fields
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [vehicleType, setVehicleType] = useState("Mini Truck");
  const [licenseNumber, setLicenseNumber] = useState("");

  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!role) return;

    if (password !== confirmPassword) {
      setErrorMsg("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      // Clean phone number for email mapping — extract last 10 digits only
      const digitsOnly = phone.replace(/\D/g, "");
      const cleanPhone = digitsOnly.slice(-10);
      const email = `user${cleanPhone}@myapp.com`;

      // 1. Supabase Auth SignUp
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password
      });

      if (authError || !authData.user) {
        setErrorMsg(authError?.message || "Failed to create authentication user.");
        setLoading(false);
        return;
      }

      const userId = authData.user.id;

      // 2. Insert into users table (no password stored - auth handled by Supabase)
      const { error: userError } = await supabase.from("users").insert({
        id: userId,
        name,
        phone,
        village: role === "farmer" ? village : null,
        preferred_language: role === "farmer" ? preferredLanguage : "en",
        role
      });

      if (userError) {
        throw new Error(`Users table insert failed: ${userError.message}`);
      }

      // 3. Role specific table inserts
      if (role === "farmer") {
        const { error: farmerError } = await supabase.from("farmers").insert({
          user_id: userId,
          village,
          preferred_language: preferredLanguage
        });

        if (farmerError) {
          throw new Error(`Farmers table insert failed: ${farmerError.message}`);
        }
      } else if (role === "driver") {
        // Insert into drivers table and retrieve created driver ID
        const { data: driverData, error: driverError } = await supabase
          .from("drivers")
          .insert({
            user_id: userId,
            vehicle_number: vehicleNumber,
            vehicle_type: vehicleType,
            license_number: licenseNumber,
            reliability_score: 94,
            completed_trips: 0,
            rating: 4.8
          })
          .select()
          .single();

        if (driverError) {
          throw new Error(`Drivers table insert failed: ${driverError.message}`);
        }

        // Insert into vehicles table with unified vehicle tier capacity linked to driver_id
        let capacityKg = 1100;
        const vLower = vehicleType.toLowerCase();
        if (vLower.includes("mini") || vLower.includes("500")) {
          capacityKg = 500;
        } else if (vLower.includes("heavy") || vLower.includes("2500")) {
          capacityKg = 2500;
        } else {
          capacityKg = 1100;
        }

        const { error: vehicleError } = await supabase.from("vehicles").insert({
          driver_id: driverData?.id ?? null,
          vehicle_number: vehicleNumber,
          vehicle_type: vehicleType,
          capacity_kg: capacityKg
        });

        if (vehicleError) {
          console.warn("Vehicle insert warning:", vehicleError.message);
          // Don't throw - vehicle is optional
        }
      }

      // Successfully registered! Establish session with sign in
      const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) {
        throw new Error(`Sign in after registration failed: ${signInError.message}`);
      }

      // Send registration SMS (non-blocking - don't wait for it)
      sendRegistrationSMS(name, phone, role).catch((err) => {
        console.warn("SMS send failed after registration:", err);
      });
      
      // Redirect to their dashboard
      if (role === "farmer") {
        router.push("/farmer");
      } else {
        router.push("/driver/loads");
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Registration failed. Please try again.");
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#fffaf0] flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative">
      <div className="absolute top-6 left-6">
        <Link href="/" className="inline-flex items-center gap-1.5 text-xs font-bold text-stone-500 hover:text-soil transition-colors">
          <ArrowLeft size={16} />
          Back to Home
        </Link>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-field/30 bg-white px-3 py-1 text-xs font-semibold text-field">
            <Languages size={14} />
            Pool Together & Save
          </div>
        </div>
        <h2 className="mt-5 text-center text-3xl font-black text-soil uppercase tracking-wide">
          Register Account
        </h2>
        <p className="mt-1.5 text-center text-xs text-stone-500">
          Step {step} of 2: {step === 1 ? "Select Platform Role" : `Enter ${role === "farmer" ? "Farmer" : "Driver"} Details`}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 border border-stone-200 shadow-panel sm:rounded-xl sm:px-10 relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-1 bg-soil" />

          {/* STEP 1: Select Role */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <p className="text-center text-sm font-semibold text-stone-700 mb-4">
                  Which type of account would you like to create?
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setRole("farmer")}
                    className={`focus-ring p-5 rounded-xl border-2 text-center transition-all flex flex-col items-center gap-2.5 ${
                      role === "farmer"
                        ? "border-soil bg-soil/5 text-soil font-black"
                        : "border-stone-200 bg-stone-50 hover:bg-stone-100 text-stone-600 font-semibold"
                    }`}
                  >
                    <span className="text-2xl">🌾</span>
                    <span className="text-sm">Farmer Account</span>
                  </button>
                  <button
                    onClick={() => setRole("driver")}
                    className={`focus-ring p-5 rounded-xl border-2 text-center transition-all flex flex-col items-center gap-2.5 ${
                      role === "driver"
                        ? "border-soil bg-soil/5 text-soil font-black"
                        : "border-stone-200 bg-stone-50 hover:bg-stone-100 text-stone-600 font-semibold"
                    }`}
                  >
                    <span className="text-2xl">🚛</span>
                    <span className="text-sm">Driver Account</span>
                  </button>
                </div>
              </div>

              <div className="bg-stone-50 border border-stone-100 rounded-lg p-3 text-[11px] text-stone-500">
                <span className="font-extrabold uppercase text-soil block mb-0.5">Admin Notice:</span>
                Admin accounts are seeded manually for security. Admins cannot self-register.
              </div>

              <button
                disabled={!role}
                onClick={() => setStep(2)}
                className="w-full focus-ring flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-soil hover:bg-soil/95 transition-all uppercase tracking-wider disabled:opacity-50"
              >
                Continue
              </button>
            </div>
          )}

          {/* STEP 2: Enter Details */}
          {step === 2 && role && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-stone-100 mb-3">
                <span className="text-xs font-black text-soil uppercase">Role: {role}</span>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-[11px] text-stone-400 hover:text-stone-600 font-bold hover:underline"
                >
                  Change Role
                </button>
              </div>

              {/* Common Inputs */}
              <div>
                <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Arumugam"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                />
              </div>

              <div>
                <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                  Phone Number
                </label>
                <input
                  type="tel"
                  placeholder="e.g. +91 90030 11224"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                  className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                />
              </div>

              {/* Farmer Specific Inputs */}
              {role === "farmer" && (
                <>
                  <div>
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                      Village
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Melma"
                      value={village}
                      onChange={(e) => setVillage(e.target.value)}
                      required
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                      Preferred Language
                    </label>
                    <select
                      value={preferredLanguage}
                      onChange={(e) => setPreferredLanguage(e.target.value)}
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 bg-white"
                    >
                      <option value="ta">Tamil (தமிழ்)</option>
                      <option value="hi">Hindi (हिंदी)</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                </>
              )}

              {/* Driver Specific Inputs */}
              {role === "driver" && (
                <>
                  <div>
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                      Vehicle Number
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. TN 11 AB 4472"
                      value={vehicleNumber}
                      onChange={(e) => setVehicleNumber(e.target.value)}
                      required
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                      Vehicle Type
                    </label>
                    <select
                      value={vehicleType}
                      onChange={(e) => setVehicleType(e.target.value)}
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 bg-white"
                    >
                      <option value="Mini Truck">Mini Truck (500 kg)</option>
                      <option value="Standard Truck">Standard Truck (1100 kg)</option>
                      <option value="Heavy Truck">Heavy Truck (2500 kg)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                      Driving License Number
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. DL-1420230005524"
                      value={licenseNumber}
                      onChange={(e) => setLicenseNumber(e.target.value)}
                      required
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                    />
                  </div>
                </>
              )}

              {/* Password Inputs */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                  />
                </div>
                <div>
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                    Confirm
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                  />
                </div>
              </div>

              {errorMsg && (
                <div className="rounded-lg bg-chilli/10 border border-chilli/20 p-3 flex items-start gap-2 text-chilli animate-fadeIn">
                  <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                  <span className="text-xs font-bold leading-tight">{errorMsg}</span>
                </div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full focus-ring flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-soil hover:bg-soil/95 transition-all uppercase tracking-wider disabled:opacity-50"
                >
                  {loading ? "Registering..." : "Register & Sign In"}
                </button>
              </div>
            </form>
          )}

          <div className="mt-5 text-center text-xs">
            <span className="text-stone-500">Already have an account? </span>
            <Link href="/login" className="font-bold text-soil hover:underline">
              Log in instead
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
