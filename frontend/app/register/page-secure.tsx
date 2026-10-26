"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Languages, 
  AlertCircle, 
  ArrowLeft, 
  CheckCircle2, 
  Eye, 
  EyeOff,
  Shield,
  MapPin 
} from "lucide-react";
import Link from "next/link";
import PasswordStrength, { calculatePasswordStrength } from "@/components/PasswordStrength";
import OTPVerification from "@/components/OTPVerification";

const API_BASE = "http://localhost:8000";

export default function SecureRegisterPage() {
  const [step, setStep] = useState(1);
  const [role, setRole] = useState<"farmer" | "driver" | null>(null);

  // Common Fields
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Location fields (enhanced)
  const [village, setVillage] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [state, setState] = useState("");
  const [pinCode, setPinCode] = useState("");

  // Farmer Fields
  const [preferredLanguage, setPreferredLanguage] = useState("ta");

  // Driver Fields
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [vehicleType, setVehicleType] = useState("Standard Truck");
  const [licenseNumber, setLicenseNumber] = useState("");

  // OTP verification
  const [userId, setUserId] = useState("");
  const [phoneVerified, setPhoneVerified] = useState(false);
  const [showOTPStep, setShowOTPStep] = useState(false);

  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const validatePassword = () => {
    if (password !== confirmPassword) {
      setErrorMsg("Passwords do not match.");
      return false;
    }

    const strength = calculatePasswordStrength(password);
    if (strength.score < 30) {
      setErrorMsg("Password is too weak. Please use a stronger password.");
      return false;
    }

    return true;
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!role) {
      setErrorMsg("Please select a role.");
      return;
    }

    if (!validatePassword()) {
      return;
    }

    setLoading(true);

    try {
      const requestBody: any = {
        name,
        phone,
        password,
        role,
        village: role === "farmer" ? village || city : null,
        city,
        district,
        state,
        pin_code: pinCode,
        preferred_language: role === "farmer" ? preferredLanguage : "en",
      };

      if (role === "driver") {
        if (!vehicleNumber || !vehicleType || !licenseNumber) {
          setErrorMsg("All driver fields are required.");
          setLoading(false);
          return;
        }

        requestBody.vehicle_number = vehicleNumber;
        requestBody.vehicle_type = vehicleType;
        requestBody.license_number = licenseNumber;
      }

      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      // Store user ID for OTP verification
      setUserId(data.user_id);
      
      // Move to OTP verification step
      setShowOTPStep(true);
      setStep(3);
      setLoading(false);

    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Registration failed. Please try again.");
      setLoading(false);
    }
  };

  const handleOTPVerified = async () => {
    setPhoneVerified(true);
    
    // For drivers, show verification instructions
    if (role === "driver") {
      setStep(4);
    } else {
      // For farmers, redirect to dashboard
      router.push("/farmer");
    }
  };

  const handleVerifyDocuments = async () => {
    if (!userId) return;

    setLoading(true);
    setErrorMsg("");

    try {
      // Get driver ID first
      const statusResponse = await fetch(`${API_BASE}/api/auth/account-status/${userId}`);
      const statusData = await statusResponse.json();

      if (!statusData.driver_id) {
        throw new Error("Driver ID not found");
      }

      const driverId = statusData.driver_id;

      // Verify vehicle
      const vehicleResponse = await fetch(`${API_BASE}/api/auth/verify-vehicle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          driver_id: driverId,
          vehicle_number: vehicleNumber,
          owner_name: name,
        }),
      });

      if (!vehicleResponse.ok) {
        throw new Error("Vehicle verification request failed");
      }

      // Verify license
      const licenseResponse = await fetch(`${API_BASE}/api/auth/verify-license`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          driver_id: driverId,
          license_number: licenseNumber,
          holder_name: name,
        }),
      });

      if (!licenseResponse.ok) {
        throw new Error("License verification request failed");
      }

      // Redirect to driver dashboard
      router.push("/driver/loads");

    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Verification submission failed.");
    } finally {
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
            <Shield size={14} />
            Secure Registration
          </div>
        </div>
        <h2 className="mt-5 text-center text-3xl font-black text-soil uppercase tracking-wide">
          Register Account
        </h2>
        <p className="mt-1.5 text-center text-xs text-stone-500">
          {step === 1 && "Step 1 of 4: Select Platform Role"}
          {step === 2 && `Step 2 of 4: Enter ${role === "farmer" ? "Farmer" : "Driver"} Details`}
          {step === 3 && "Step 3 of 4: Verify Phone Number"}
          {step === 4 && "Step 4 of 4: Document Verification Status"}
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
                <span className="font-extrabold uppercase text-soil block mb-0.5">Security Notice:</span>
                All accounts require phone verification via OTP. Driver accounts require additional document verification.
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
                  Full Name *
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
                  Phone Number *
                </label>
                <input
                  type="tel"
                  placeholder="e.g. +91 90030 11224"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                  className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850"
                />
                <p className="mt-1 text-xs text-stone-500">Will be verified via OTP</p>
              </div>

              {/* Location Fields */}
              <div className="bg-stone-50 border border-stone-200 rounded-lg p-3 space-y-3">
                <div className="flex items-center gap-2 text-xs font-black text-soil uppercase">
                  <MapPin size={14} />
                  Location Details
                </div>
                
                {role === "farmer" && (
                  <div>
                    <label className="block text-xs font-semibold text-stone-600 mb-1">
                      Village / Town *
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Melma"
                      value={village}
                      onChange={(e) => setVillage(e.target.value)}
                      required
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 bg-white"
                    />
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-stone-600 mb-1">
                      City
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Chennai"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-stone-600 mb-1">
                      District
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Kancheepuram"
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 bg-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-stone-600 mb-1">
                      State
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Tamil Nadu"
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-stone-600 mb-1">
                      PIN Code
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 600001"
                      value={pinCode}
                      onChange={(e) => setPinCode(e.target.value)}
                      maxLength={6}
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 bg-white"
                    />
                  </div>
                </div>
              </div>

              {/* Farmer Specific Inputs */}
              {role === "farmer" && (
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
              )}

              {/* Driver Specific Inputs */}
              {role === "driver" && (
                <>
                  <div>
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                      Vehicle Number *
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. TN 11 AB 4472"
                      value={vehicleNumber}
                      onChange={(e) => setVehicleNumber(e.target.value.toUpperCase())}
                      required
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 uppercase"
                    />
                    <p className="mt-1 text-xs text-stone-500">Will be verified</p>
                  </div>
                  <div>
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                      Vehicle Type *
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
                      Driving License Number *
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. DL-1420230005524"
                      value={licenseNumber}
                      onChange={(e) => setLicenseNumber(e.target.value.toUpperCase())}
                      required
                      className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 uppercase"
                    />
                    <p className="mt-1 text-xs text-stone-500">Will be verified</p>
                  </div>
                </>
              )}

              {/* Password Inputs */}
              <div>
                <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                  Password *
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                  Confirm Password *
                </label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-850 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Password Strength */}
              {password && <PasswordStrength password={password} />}

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
                  {loading ? "Creating Account..." : "Create Account"}
                </button>
              </div>
            </form>
          )}

          {/* STEP 3: OTP Verification */}
          {step === 3 && showOTPStep && userId && (
            <div className="space-y-6">
              <OTPVerification
                userId={userId}
                phone={phone}
                onVerified={handleOTPVerified}
                autoSend={true}
              />
            </div>
          )}

          {/* STEP 4: Document Verification Status (Drivers only) */}
          {step === 4 && role === "driver" && phoneVerified && (
            <div className="space-y-6">
              <div className="text-center space-y-3">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-soil/10">
                  <CheckCircle2 className="h-8 w-8 text-soil" />
                </div>
                <h3 className="text-lg font-black text-soil uppercase">Registration Complete!</h3>
                <p className="text-sm text-stone-600">
                  Your phone number has been verified. Now we'll verify your vehicle and license documents.
                </p>
              </div>

              <div className="space-y-3">
                <div className="bg-stone-50 border border-stone-200 rounded-lg p-3">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-soil/10 flex items-center justify-center">
                      <span className="text-sm font-bold text-soil">1</span>
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-stone-700 mb-1">Vehicle: {vehicleNumber}</p>
                      <p className="text-xs text-stone-500">Submitted for verification</p>
                    </div>
                  </div>
                </div>

                <div className="bg-stone-50 border border-stone-200 rounded-lg p-3">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-soil/10 flex items-center justify-center">
                      <span className="text-sm font-bold text-soil">2</span>
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-stone-700 mb-1">License: {licenseNumber}</p>
                      <p className="text-xs text-stone-500">Submitted for verification</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-lg bg-field/5 border border-field/20 p-3 text-xs text-stone-600">
                <p className="font-bold text-field mb-1">⏱️ Verification Timeline</p>
                <p>Admin will review your documents within 24 hours. You'll be notified via SMS once approved.</p>
              </div>

              {errorMsg && (
                <div className="rounded-lg bg-chilli/10 border border-chilli/20 p-3 flex items-start gap-2 text-chilli">
                  <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                  <span className="text-xs font-bold leading-tight">{errorMsg}</span>
                </div>
              )}

              <button
                onClick={handleVerifyDocuments}
                disabled={loading}
                className="w-full focus-ring flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-soil hover:bg-soil/95 transition-all uppercase tracking-wider disabled:opacity-50"
              >
                {loading ? "Submitting..." : "Continue to Dashboard"}
              </button>
            </div>
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
