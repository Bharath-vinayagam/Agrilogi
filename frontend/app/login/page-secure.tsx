"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Languages, 
  AlertCircle, 
  ArrowLeft, 
  Eye, 
  EyeOff,
  Shield,
  CheckCircle2,
  Clock,
  XCircle
} from "lucide-react";
import Link from "next/link";

const API_BASE = "http://localhost:8000";

interface VerificationStatus {
  phone_verified: boolean;
  vehicle_verification_status?: string;
  license_verification_status?: string;
  account_status?: string;
  can_accept_loads?: boolean;
}

export default function SecureLoginPage() {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState<"farmer" | "driver" | "admin">("farmer");
  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus | null>(null);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setVerificationStatus(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, password, role }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed");
      }

      // Check verification status
      if (!data.phone_verified) {
        setErrorMsg("Phone number not verified. Please complete registration.");
        setLoading(false);
        return;
      }

      // Store verification status for drivers
      if (data.user.role === "driver") {
        setVerificationStatus({
          phone_verified: data.phone_verified,
          vehicle_verification_status: data.user.vehicle_verification_status,
          license_verification_status: data.user.license_verification_status,
          account_status: data.user.account_status,
          can_accept_loads: data.user.can_accept_loads,
        });

        // Show warning if verifications are pending
        if (data.user.account_status === "pending_verification") {
          setErrorMsg(
            "Your documents are pending verification. You can view available loads but cannot accept them until verification is complete."
          );
        }
      }

      // Store session
      localStorage.setItem("agrilogi_session", JSON.stringify({
        user: data.user,
        session: data.session,
      }));

      // Redirect based on role
      setLoading(false);
      setTimeout(() => {
        if (data.user.role === "farmer") {
          router.push("/farmer");
        } else if (data.user.role === "driver") {
          router.push("/driver/loads");
        } else if (data.user.role === "admin") {
          router.push("/admin");
        }
      }, 1000);

    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Login failed. Please try again.");
      setLoading(false);
    }
  };

  const handleQuickDemoLogin = () => {
    let mockUser: any = {};
    if (role === "farmer") {
      mockUser = {
        id: "demo-farmer-id",
        name: "Arumugam (Demo)",
        phone: phone || "9003011224",
        role: "farmer",
        village: "Melma",
        preferred_language: "ta",
        is_mock: true
      };
    } else if (role === "driver") {
      mockUser = {
        id: "demo-driver-id",
        name: "Shyam (Demo)",
        phone: phone || "9486456584",
        role: "driver",
        driverId: "demo-driver-uuid",
        reliability_score: 98,
        completed_trips: 42,
        rating: 4.9,
        vehicle_verification_status: "verified",
        license_verification_status: "verified",
        account_status: "active",
        is_mock: true
      };
    } else {
      mockUser = {
        id: "demo-admin-id",
        name: "Admin (Demo)",
        phone: phone || "9999999999",
        role: "admin",
        is_mock: true
      };
    }

    const mockSession = {
      user: {
        id: mockUser.id,
        email: `user${mockUser.phone}@agrilogi.com`,
        user_metadata: mockUser
      }
    };

    localStorage.setItem("kb_demo_session", JSON.stringify(mockSession));
    
    if (role === "farmer") {
      router.push("/farmer");
    } else if (role === "driver") {
      router.push("/driver/loads");
    } else {
      router.push("/admin");
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "verified":
        return (
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-soil/10 text-soil text-xs font-bold">
            <CheckCircle2 size={12} />
            Verified
          </div>
        );
      case "pending":
      case "manual_review":
        return (
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-yellow-500/10 text-yellow-700 text-xs font-bold">
            <Clock size={12} />
            Pending
          </div>
        );
      case "failed":
        return (
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-chilli/10 text-chilli text-xs font-bold">
            <XCircle size={12} />
            Failed
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <main className="min-h-screen bg-[#fffaf0] flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative">
      {/* Back to Home Link */}
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
            Secure Login
          </div>
        </div>
        <h2 className="mt-5 text-center text-3xl font-black text-soil uppercase tracking-wide">
          Login to Agrilogi
        </h2>
        <p className="mt-1.5 text-center text-xs text-stone-500">
          Enter credentials below to access your logistics workspace.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 border border-stone-200 shadow-panel sm:rounded-xl sm:px-10 relative overflow-hidden">
          {/* Subtle Accent Line */}
          <div className="absolute top-0 inset-x-0 h-1 bg-soil" />

          <form className="space-y-5" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                Preferred Workspace Role
              </label>
              <div className="grid grid-cols-3 gap-2">
                {["farmer", "driver", "admin"].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r as any)}
                    className={`focus-ring py-2 rounded-lg text-xs font-bold capitalize border transition-all ${
                      role === r
                        ? "bg-soil text-white border-soil"
                        : "bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="phone" className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                Phone Number
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                placeholder="e.g. +91 90030 11224"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-800 placeholder-stone-400"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="focus-ring block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-800 placeholder-stone-400 pr-10"
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

            {/* Verification Status Display (for drivers) */}
            {verificationStatus && role === "driver" && (
              <div className="rounded-lg bg-stone-50 border border-stone-200 p-3 space-y-2">
                <p className="text-xs font-bold text-stone-700 mb-2">Verification Status</p>
                
                <div className="flex items-center justify-between">
                  <span className="text-xs text-stone-600">Phone Number</span>
                  {getStatusBadge(verificationStatus.phone_verified ? "verified" : "pending")}
                </div>

                {verificationStatus.vehicle_verification_status && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-stone-600">Vehicle Registration</span>
                    {getStatusBadge(verificationStatus.vehicle_verification_status)}
                  </div>
                )}

                {verificationStatus.license_verification_status && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-stone-600">Driving License</span>
                    {getStatusBadge(verificationStatus.license_verification_status)}
                  </div>
                )}

                {verificationStatus.account_status && (
                  <div className="pt-2 mt-2 border-t border-stone-200">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-stone-700">Account Status</span>
                      <span className="text-xs font-bold capitalize text-stone-800">
                        {verificationStatus.account_status.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                )}

                {!verificationStatus.can_accept_loads && (
                  <div className="pt-2 rounded-lg bg-yellow-500/5 border border-yellow-500/20 p-2">
                    <p className="text-xs text-yellow-700 font-semibold">
                      ⚠️ Complete verification to accept loads
                    </p>
                  </div>
                )}
              </div>
            )}

            {errorMsg && (
              <div className="rounded-lg bg-chilli/10 border border-chilli/20 p-3 flex items-start gap-2 text-chilli animate-fadeIn">
                <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                <span className="text-xs font-bold leading-tight">{errorMsg}</span>
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full focus-ring flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-soil hover:bg-soil/95 transition-all uppercase tracking-wider disabled:opacity-50"
              >
                {loading ? "Authenticating..." : "Login"}
              </button>
            </div>

            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-stone-200"></div>
              </div>
              <div className="relative flex justify-center text-[10px] uppercase font-extrabold">
                <span className="bg-white px-2 text-stone-400">Or Bypass Rate Limits</span>
              </div>
            </div>

            <div>
              <button
                type="button"
                onClick={handleQuickDemoLogin}
                className="w-full focus-ring flex justify-center py-2.5 px-4 border border-soil/30 rounded-lg shadow-sm text-xs font-black text-soil bg-soil/5 hover:bg-soil/10 transition-all uppercase tracking-wider"
              >
                ⚡ Enter in Demo Mode ({role})
              </button>
            </div>
          </form>

          <div className="mt-5 text-center text-xs">
            <span className="text-stone-500">New to the platform? </span>
            <Link href="/register" className="font-bold text-soil hover:underline">
              Create an account
            </Link>
          </div>

          <div className="mt-3 text-center">
            <Link href="/forgot-password" className="text-xs text-stone-500 hover:text-soil hover:underline">
              Forgot password?
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
