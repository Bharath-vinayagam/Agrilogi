/**
 * services/pricingConfig.ts
 *
 * Frontend offline pricing engine and dynamic configuration sync.
 * Mirrors the single source of truth from the backend rate_config.py and mandi_config.py.
 */

// Version number for cache invalidation - increment when config structure changes
const CONFIG_VERSION = 2;

export interface VehicleClass {
  name: string;
  capacity_kg: number;
  cost_per_km: number;          // Farmer-side rate (what farmers pay per km share)
  base_fee: number;
  fuel_cost_per_km: number;     // Driver's actual diesel cost per km
  driver_cost_per_km: number;   // Driver's own labour/earnings per km
}

export interface MandiCoordinate {
  lat: number;
  lng: number;
  name?: string;
}

export interface PricingConfig {
  version?: number;
  vehicle_classes: Record<string, VehicleClass>;
  min_rate_per_kg: number;
  fallback_rate_per_kg: number;
  mandi_coords: Record<string, MandiCoordinate>;
}

// Default offline config mirroring backend rate_config.py & mandi_config.py
const DEFAULT_PRICING_CONFIG: PricingConfig = {
  version: CONFIG_VERSION,
  vehicle_classes: {
    mini: {
      name: "mini",
      capacity_kg: 500,
      cost_per_km: 12,
      base_fee: 150,
      fuel_cost_per_km: 8,
      driver_cost_per_km: 2,
    },
    standard: {
      name: "standard",
      capacity_kg: 1100,
      cost_per_km: 20,
      base_fee: 250,
      fuel_cost_per_km: 12,
      driver_cost_per_km: 3,
    },
    heavy: {
      name: "heavy",
      capacity_kg: 2500,
      cost_per_km: 28,
      base_fee: 400,
      fuel_cost_per_km: 18,
      driver_cost_per_km: 4,
    }
  },
  min_rate_per_kg: 3,
  fallback_rate_per_kg: 9,
  mandi_coords: {
    "koyambedu mandi": { lat: 13.0716, lng: 80.1945, name: "Koyambedu Mandi, Chennai" },
    "madurai mandi": { lat: 9.9252, lng: 78.1198, name: "Madurai Mandi" },
    "coimbatore mandi": { lat: 11.0168, lng: 76.9558, name: "Coimbatore Mandi" },
    "salem mandi": { lat: 11.6643, lng: 78.1460, name: "Salem Mandi" },
    "trichy mandi": { lat: 10.7905, lng: 78.7047, name: "Trichy Mandi" },
    "vellore mandi": { lat: 12.9165, lng: 79.1325, name: "Vellore Mandi" },
    "delhi mandi": { lat: 28.7196, lng: 77.1724, name: "Azadpur Mandi, Delhi" }
  }
};

let activeConfig: PricingConfig = DEFAULT_PRICING_CONFIG;

// Load persisted config from localStorage if available
// Clear cache if version mismatch or old structure
if (typeof window !== "undefined") {
  try {
    const saved = localStorage.getItem("agrilogi_pricing_config");
    if (saved) {
      const parsed = JSON.parse(saved);
      // Check version match and structure validity
      if (parsed.version === CONFIG_VERSION) {
        activeConfig = parsed;
        console.log("[Pricing] Using cached config v" + CONFIG_VERSION);
      } else {
        // Version mismatch or missing — clear cache
        localStorage.removeItem("agrilogi_pricing_config");
        console.log("[Pricing] Cache cleared due to version mismatch");
      }
    }
  } catch (e) {
    console.error("Failed to read saved pricing config:", e);
    localStorage.removeItem("agrilogi_pricing_config");
  }
}

/**
 * Fetch latest rates and coordinates from the backend and cache them.
 */
export async function syncPricingConfig(): Promise<void> {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/api/config/pricing`, { cache: "no-store" });
    if (res.ok) {
      const data: PricingConfig = await res.json();
      data.version = CONFIG_VERSION; // Add version to backend data
      activeConfig = data;
      if (typeof window !== "undefined") {
        localStorage.setItem("agrilogi_pricing_config", JSON.stringify(data));
      }
      console.log("[Pricing] Synchronized latest pricing config from backend v" + CONFIG_VERSION);
    }
  } catch (err) {
    console.warn("[Pricing] Could not sync pricing config from backend, using cached/default.", err);
  }
}

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371.0;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dlat = toRad(lat2 - lat1);
  const dlng = toRad(lng2 - lng1);
  const a =
    Math.sin(dlat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dlng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(a));
}

function getMandiCoords(destination: string): MandiCoordinate | null {
  if (!destination) return null;
  const key = destination.trim().toLowerCase();
  for (const [k, coords] of Object.entries(activeConfig.mandi_coords)) {
    if (k.includes(key) || key.includes(k)) {
      return coords;
    }
  }
  return null;
}

function getVehicleClass(weightKg: number): VehicleClass {
  const classes = activeConfig.vehicle_classes;
  for (const name of ["mini", "standard", "heavy"]) {
    if (classes[name] && weightKg <= classes[name].capacity_kg) {
      return classes[name];
    }
  }
  return classes.heavy || DEFAULT_PRICING_CONFIG.vehicle_classes.heavy;
}

/**
 * Calculate individual transport cost for a farmer hiring a truck alone.
 */
export function calculateIndividualCostOffline(
  weightKg: number,
  village?: string,
  destination: string = "Koyambedu Mandi",
  farmerLat?: number | null,
  farmerLng?: number | null
): number {
  if (!weightKg || weightKg <= 0) return 0;

  if (farmerLat != null && farmerLng != null && destination) {
    const mandi = getMandiCoords(destination);
    if (mandi) {
      const distanceKm = haversineKm(farmerLat, farmerLng, mandi.lat, mandi.lng);
      const vClass = getVehicleClass(weightKg);
      const weightFactor = weightKg / vClass.capacity_kg;
      const calculated = vClass.base_fee + distanceKm * vClass.cost_per_km * weightFactor;
      const floorCost = weightKg * activeConfig.min_rate_per_kg;
      return Math.max(Math.round(calculated), floorCost);
    }
  }

  // Fallback when GPS or mandi coordinates are unknown (₹9/kg)
  return Math.round(weightKg * activeConfig.fallback_rate_per_kg);
}

export interface DriverTripCost {
  vehicleClass: string;
  distanceKm: number;
  fuelCost: number;
  driverWage: number;
  totalDriverCost: number;
  suggestedBidMin: number;
  suggestedBidMax: number;
}

/**
 * Calculate a driver's actual trip cost and suggested bid range.
 * Uses real diesel/fuel rates (not farmer pricing rates).
 * All costs are distance-based — no flat daily wage.
 */
export function calculateDriverTripCost(
  distanceKm: number,
  weightKg: number
): DriverTripCost {
  const vClass = getVehicleClass(weightKg);
  // Guard against stale cached config missing the new fields
  const fuelRate = vClass.fuel_cost_per_km ?? (vClass.name === "mini" ? 8 : vClass.name === "heavy" ? 18 : 12);
  const wageRate = vClass.driver_cost_per_km ?? (vClass.name === "mini" ? 2 : vClass.name === "heavy" ? 4 : 3);

  const fuel = Math.round(distanceKm * fuelRate);
  const wage = Math.round(distanceKm * wageRate);
  const totalCost = fuel + wage;
  return {
    vehicleClass: vClass.name,
    distanceKm: Math.round(distanceKm),
    fuelCost: fuel,
    driverWage: wage,
    totalDriverCost: totalCost,
    suggestedBidMin: Math.round(totalCost * 1.2),
    suggestedBidMax: Math.round(totalCost * 1.5),
  };
}
