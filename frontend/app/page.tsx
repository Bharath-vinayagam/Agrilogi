"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/services/supabase";
import { syncPricingConfig } from "@/services/pricingConfig";
import { Languages, Headphones, Route, Truck } from "lucide-react";
import Link from "next/link";

export default function LandingPage() {
  const [checking, setChecking] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Synchronize latest pricing configuration from backend
    syncPricingConfig();

    async function checkUser() {
      let session: any = null;
      if (typeof window !== "undefined") {
        const localDemo = localStorage.getItem("kb_demo_session");
        if (localDemo) {
          try {
            session = JSON.parse(localDemo);
          } catch (e) {
            console.error("Failed to parse demo session", e);
          }
        }
      }

      if (session && session.user?.user_metadata) {
        const role = session.user.user_metadata.role;
        if (role === "farmer") {
          router.push("/farmer");
        } else if (role === "driver") {
          router.push("/driver/loads");
        } else if (role === "admin") {
          router.push("/admin");
        }
        return;
      }

      const { data: { session: sbSession } } = await supabase.auth.getSession();
      if (sbSession) {
        const { data: profile } = await supabase
          .from("users")
          .select("role")
          .eq("id", sbSession.user.id)
          .single();

        if (profile) {
          if (profile.role === "farmer") {
            router.push("/farmer");
          } else if (profile.role === "driver") {
            router.push("/driver/loads");
          } else if (profile.role === "admin") {
            router.push("/admin");
          }
          return;
        }
      }
      setChecking(false);
    }
    checkUser();
  }, [router]);

  if (checking) {
    return (
      <div className="min-h-screen bg-[#fffaf0] flex items-center justify-center">
        <p className="text-stone-500 font-semibold animate-pulse">Loading Agrilogi...</p>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#fffaf0] flex flex-col justify-between">
      {/* Top Banner Navigation */}
      <header className="border-b border-stone-200 bg-[#fffaf0]/80 backdrop-blur-md sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-4 py-4 lg:px-6 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="text-xl font-black text-soil tracking-wide">Agrilogi</span>
            <span className="text-[10px] uppercase font-bold text-river bg-river/10 px-2 py-0.5 rounded-full">v2.0</span>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-field/30 bg-white px-3.5 py-1 text-xs font-semibold text-field shadow-sm">
            <Languages size={14} />
            Tamil / Hindi / English Supported
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="mx-auto max-w-4xl px-4 py-16 text-center space-y-8 flex-1 flex flex-col justify-center">
        <div className="space-y-4">
          <h1 className="text-5xl font-black tracking-normal text-soil sm:text-6xl md:text-7xl animate-fadeIn">
            AGRILOGI
          </h1>
          <p className="text-lg sm:text-xl md:text-2xl font-bold text-stone-700 tracking-wide max-w-2xl mx-auto leading-relaxed">
            AI-Powered Cooperative Logistics Platform
          </p>
          <p className="text-sm text-stone-500 max-w-lg mx-auto">
            Helping small agricultural farmers pool transport loads, participate in smart driver bidding, and secure freshness logistics.
          </p>
        </div>

        {/* Buttons Grid */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center max-w-xs sm:max-w-md mx-auto w-full">
          <Link
            href="/login"
            className="w-full sm:w-44 focus-ring text-center rounded-xl bg-soil py-3.5 font-bold text-white shadow-md hover:bg-soil/95 transition-all text-sm uppercase tracking-wider"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="w-full sm:w-44 focus-ring text-center rounded-xl border-2 border-soil bg-white py-3.5 font-bold text-soil hover:bg-soil/5 transition-all text-sm uppercase tracking-wider"
          >
            Register
          </Link>
        </div>

        {/* Dynamic Highlights Panel */}
        <div className="grid gap-4 sm:grid-cols-3 max-w-2xl mx-auto w-full pt-10">
          <div className="rounded-xl bg-white p-5 border border-stone-200/60 shadow-panel flex flex-col items-center hover:border-chilli/30 transition-all group">
            <div className="bg-chilli/10 p-3 rounded-xl text-chilli group-hover:scale-105 transition-transform">
              <Headphones size={22} />
            </div>
            <p className="mt-3.5 text-sm font-black text-soil">Voice call booking</p>
            <p className="mt-1 text-[11px] text-stone-500 text-center">Toll-free voice recognition helplines for non-literate farmers.</p>
          </div>
          <div className="rounded-xl bg-white p-5 border border-stone-200/60 shadow-panel flex flex-col items-center hover:border-river/30 transition-all group">
            <div className="bg-river/10 p-3 rounded-xl text-river group-hover:scale-105 transition-transform">
              <Route size={22} />
            </div>
            <p className="mt-3.5 text-sm font-black text-soil">AI clustering</p>
            <p className="mt-1 text-[11px] text-stone-500 text-center">Cooperative spatial routing to save route travel, fuel, and prevent waste.</p>
          </div>
          <div className="rounded-xl bg-white p-5 border border-stone-200/60 shadow-panel flex flex-col items-center hover:border-field/30 transition-all group">
            <div className="bg-field/10 p-3 rounded-xl text-field group-hover:scale-105 transition-transform">
              <Truck size={22} />
            </div>
            <p className="mt-3.5 text-sm font-black text-soil">Driver Bidding</p>
            <p className="mt-1 text-[11px] text-stone-500 text-center">Transparent marketplace for transporters to bid on cooperative loads.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-stone-200 py-6 text-center text-xs text-stone-500 bg-white">
        © 2026 Agrilogi Cooperative. Designed for AgriTech Hackathon Excellence.
      </footer>
    </main>
  );
}
