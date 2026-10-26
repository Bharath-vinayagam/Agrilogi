import { bids, drivers, extraction, farmerOrders, recommendation, savingsTrend } from "@/services/demoData";
import { calculateIndividualCostOffline } from "@/services/pricingConfig";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, fallback: T, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers
      },
      cache: "no-store"
    });

    if (!response.ok) {
      console.warn(`⚠️ API request failed: ${path} (status ${response.status}) - using fallback data`);
      return fallback;
    }

    const data = await response.json();
    console.log(`✅ API request success: ${path} - using database data`);
    return data as T;
  } catch (error) {
    console.error(`❌ API request error: ${path}`, error);
    console.warn(`⚠️ Using fallback demo data for: ${path}`);
    return fallback;
  }
}

export const api = {
  getOrders: async (phone?: string) => {
    const queryParam = phone ? `?phone=${encodeURIComponent(phone)}` : "";
    const raw = await request<any[]>(`/api/bookings${queryParam}`, farmerOrders);
    return raw.map(o => ({
      id: o.id,
      farmerName: o.farmer_name || o.farmerName,
      phone: o.phone,
      village: o.village,
      crop: o.crop,
      weightKg: o.weight_kg || o.weightKg,
      status: o.status,
      destination: o.destination,
      individualCost: o.individual_cost || o.individualCost,
      sharedCost: o.shared_cost || o.sharedCost,
      pickupTime: o.pickup_time || o.pickupTime || "Awaiting cluster",
      pickupDate: o.pickup_date || o.pickupDate,
      pickupSlot: o.pickup_slot || o.pickupSlot,
      isTimeFlexible: o.is_time_flexible ?? o.isTimeFlexible ?? true,
      source: o.source || "Web Dashboard",
      language: o.language || "en",
      confidence: o.confidence || null,
      reviewRequired: o.review_required || o.reviewRequired || false,
      assignedDriver: o.assigned_driver || o.assignedDriver || null,
      finalCost: o.final_cost || o.finalCost || null,
      routePass: o.route_pass || o.routePass || "unassigned",
      routeLegKm: o.route_leg_km || o.routeLegKm || null,
      assignedVehicleCapacityKg: o.assigned_vehicle_capacity_kg || o.assignedVehicleCapacityKg || null,
      lat: o.lat != null && o.lat !== "" ? Number(o.lat) : undefined,
      lng: o.lng != null && o.lng !== "" ? Number(o.lng) : undefined,
      clusterId: o.cluster_id || o.clusterId || null,
      cluster_id: o.cluster_id || o.clusterId || null
    }));
  },
  getDrivers: async () => {
    const raw = await request<any[]>("/api/drivers", drivers);
    return raw.map(d => ({
      id: d.id,
      name: d.name,
      phone: d.phone,
      vehicleNumber: d.vehicle_number || d.vehicleNumber,
      vehicleType: d.vehicle_type || d.vehicleType,
      licenseNumber: d.license_number || d.licenseNumber,
      reliabilityScore: d.reliability_score || d.reliabilityScore
    }));
  },
  getBids: async () => {
    const raw = await request<any[]>("/api/auction/bids", bids);
    return raw.map(b => ({
      id: b.id,
      driverName: b.driver_name || b.driverName,
      vehicle: b.vehicle,
      amount: b.amount,
      reliabilityScore: b.reliability_score || b.reliabilityScore,
      status: b.status
    }));
  },
  getAdminSnapshot: async () => {
    const raw = await request<any>("/api/admin/snapshot", {
      extraction,
      recommendation,
      savingsTrend,
      orders: farmerOrders,
      bids: bids
    });
    return {
      extraction: raw.extraction,
      recommendation: {
        farmers: raw.recommendation.farmers,
        totalWeightKg: raw.recommendation.total_weight_kg || raw.recommendation.totalWeightKg,
        truckUtilization: raw.recommendation.truck_utilization || raw.recommendation.truckUtilization,
        estimatedSavings: raw.recommendation.estimated_savings || raw.recommendation.estimatedSavings,
        spoilageRisk: raw.recommendation.spoilage_risk || raw.recommendation.spoilageRisk,
        departureTime: raw.recommendation.departure_time || raw.recommendation.departureTime
      },
      savingsTrend: raw.savingsTrend,
      orders: (raw.orders || []).map((o: any) => ({
        id: o.id,
        farmerName: o.farmer_name || o.farmerName,
        phone: o.phone,
        village: o.village,
        crop: o.crop,
        weightKg: o.weight_kg || o.weightKg,
        status: o.status,
        destination: o.destination,
        individualCost: o.individual_cost || o.individualCost,
        sharedCost: o.shared_cost || o.sharedCost,
        pickupTime: o.pickup_time || o.pickupTime || "Awaiting cluster",
        source: o.source || "Web Dashboard",
        language: o.language || "en",
        confidence: o.confidence || null,
        reviewRequired: o.review_required || o.reviewRequired || false,
        lat: o.lat != null && o.lat !== "" ? Number(o.lat) : undefined,
        lng: o.lng != null && o.lng !== "" ? Number(o.lng) : undefined,
        clusterId: o.cluster_id || o.clusterId || null,
        cluster_id: o.cluster_id || o.clusterId || null,
        pickupDate: o.pickup_date || o.pickupDate,
        pickupSlot: o.pickup_slot || o.pickupSlot,
        isTimeFlexible: o.is_time_flexible ?? o.isTimeFlexible ?? true,
        assignedDriver: o.assigned_driver || o.assignedDriver || null,
        finalCost: o.final_cost || o.finalCost || null,
        routePass: o.route_pass || o.routePass || "unassigned",
        routeLegKm: o.route_leg_km || o.routeLegKm || null,
        assignedVehicleCapacityKg: o.assigned_vehicle_capacity_kg || o.assignedVehicleCapacityKg || null
      })),
      bids: (raw.bids || []).map((b: any) => ({
        id: b.id,
        driverName: b.driver_name || b.driverName,
        vehicle: b.vehicle,
        amount: b.amount,
        reliabilityScore: b.reliability_score || b.reliabilityScore,
        status: b.status
      }))
    };
  },
  createBooking: async (payload: any) => {
    const o = await request<any>("/api/bookings", null, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    const wKg = Number(payload.weight_kg || payload.weightKg);
    const indivCost = calculateIndividualCostOffline(wKg, payload.village, payload.destination);
    const actualOrder = o || {
      id: `KB${Math.floor(1000 + Math.random() * 9000)}`,
      farmer_name: payload.farmer_name || payload.farmerName,
      phone: payload.phone,
      village: payload.village,
      crop: payload.crop,
      weight_kg: wKg,
      status: "Pending",
      destination: payload.destination || "Koyambedu Mandi",
      individual_cost: indivCost,
      shared_cost: indivCost,
      route_pass: "unassigned",
      pickup_time: "Awaiting cluster",
      source: payload.source || "Web Dashboard",
      language: payload.language || "en",
      confidence: null,
      review_required: false
    };
    return {
      id: actualOrder.id,
      farmerName: actualOrder.farmer_name || actualOrder.farmerName,
      phone: actualOrder.phone,
      village: actualOrder.village,
      crop: actualOrder.crop,
      weightKg: actualOrder.weight_kg || actualOrder.weightKg,
      status: actualOrder.status,
      destination: actualOrder.destination,
      individualCost: actualOrder.individual_cost || actualOrder.individualCost,
      sharedCost: actualOrder.shared_cost || actualOrder.sharedCost,
      pickupTime: actualOrder.pickup_time || actualOrder.pickupTime || "Awaiting cluster",
      source: actualOrder.source || "Web Dashboard",
      language: actualOrder.language || "en",
      confidence: actualOrder.confidence || null,
      reviewRequired: actualOrder.review_required || actualOrder.reviewRequired || false
    };
  },
  submitBid: async (payload: any) => {
    const b = await request<any>("/api/auction/bids", null, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    const actualBid = b || {
      id: payload.id || `BID-${Date.now()}`,
      driver_name: payload.driver_name || payload.driverName || "You",
      vehicle: payload.vehicle || "Mini Truck",
      amount: payload.amount,
      reliability_score: payload.reliability_score || payload.reliabilityScore || 94,
      status: "Open"
    };
    return {
      id: actualBid.id,
      driverName: actualBid.driver_name || actualBid.driverName,
      vehicle: actualBid.vehicle,
      amount: actualBid.amount,
      reliabilityScore: actualBid.reliability_score || actualBid.reliabilityScore,
      status: actualBid.status
    };
  },
  acceptBid: async (bidId: string) => {
    return await request<any>(`/api/auction/bids/${bidId}/accept`, { success: false }, {
      method: "POST"
    });
  },
  updateBooking: async (id: string, payload: any) => {
    const body = {
      farmer_name: payload.farmerName,
      phone: payload.phone,
      village: payload.village,
      crop: payload.crop,
      weight_kg: Number(payload.weightKg),
      destination: payload.destination || "Koyambedu Mandi"
    };
    const o = await request<any>(`/api/bookings/${id}`, null, {
      method: "PUT",
      body: JSON.stringify(body)
    });
    const wKg = Number(payload.weightKg);
    const indivCost = calculateIndividualCostOffline(wKg, payload.village, payload.destination);
    const actualOrder = o || {
      id: id,
      farmer_name: payload.farmerName,
      phone: payload.phone,
      village: payload.village,
      crop: payload.crop,
      weight_kg: wKg,
      status: "Pending",
      destination: payload.destination || "Koyambedu Mandi",
      individual_cost: indivCost,
      shared_cost: indivCost,
      route_pass: "unassigned",
      pickup_time: "Awaiting cluster",
      source: "Web Dashboard",
      language: "en",
      confidence: null,
      review_required: false
    };
    return {
      id: actualOrder.id,
      farmerName: actualOrder.farmer_name || actualOrder.farmerName,
      phone: actualOrder.phone,
      village: actualOrder.village,
      crop: actualOrder.crop,
      weightKg: actualOrder.weight_kg || actualOrder.weightKg,
      status: actualOrder.status,
      destination: actualOrder.destination,
      individualCost: actualOrder.individual_cost || actualOrder.individualCost,
      sharedCost: actualOrder.shared_cost || actualOrder.sharedCost,
      pickupTime: actualOrder.pickup_time || actualOrder.pickupTime || "Awaiting cluster",
      source: actualOrder.source || "Web Dashboard",
      language: actualOrder.language || "en",
      confidence: actualOrder.confidence || null,
      reviewRequired: actualOrder.review_required || actualOrder.reviewRequired || false
    };
  },
  uploadVoice: async (formData: FormData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/voice/upload`, {
        method: "POST",
        body: formData
      });
      if (!response.ok) {
        const errJson = await response.json().catch(() => null);
        throw new Error(errJson?.detail || "Voice processing failed");
      }
      const data = await response.json();
      return {
        id: data.id,
        transcript: data.transcript,
        extracted: data.extracted,
        confidence: data.confidence,
        reviewRequired: data.review_required,
        booking: data.booking ? {
          id: data.booking.id,
          farmerName: data.booking.farmer_name,
          phone: data.booking.phone,
          village: data.booking.village,
          crop: data.booking.crop,
          weightKg: data.booking.weight_kg,
          status: data.booking.status,
          destination: data.booking.destination,
          individualCost: data.booking.individual_cost,
          sharedCost: data.booking.shared_cost,
          pickupTime: data.booking.pickup_time || "Awaiting cluster",
          source: data.booking.source || "Voice Call",
          language: data.booking.language || "en",
          confidence: data.booking.confidence || null,
          reviewRequired: data.booking.review_required || false
        } : null
      };
    } catch (err: any) {
      console.warn("Helpline voice processing warning:", err?.message || err);
      const transcriptText = ((formData.get("transcript_text") as string) || "").trim();
      const farmerName = ((formData.get("farmer_name") as string) || "").trim() || "Farmer";

      // If the user actually spoke and browser speech recognition captured it, extract from THEIR actual speech
      if (transcriptText) {
        const text = transcriptText.toLowerCase();

        // Check Tamil and Hindi phonetic weight words first
        let weight = 0;
        let weightConfidence = 45;
        if (/நான்\s*ஒரு|நானூறு|நாலு\s*நூறு|naanooru|चार\s*सौ/i.test(transcriptText)) {
          weight = 400;
          weightConfidence = 95;
        } else if (/நூறு|एक\s*सौ/i.test(transcriptText)) {
          weight = 100;
          weightConfidence = 95;
        } else if (/இருநூறு|இரண்டு\s*நூறு|दो\s*सौ/i.test(transcriptText)) {
          weight = 200;
          weightConfidence = 95;
        } else if (/முந்நூறு|மூன்று\s*நூறு|तीन\s*सौ/i.test(transcriptText)) {
          weight = 300;
          weightConfidence = 95;
        } else if (/ஐந்நூறு|ஐந்து\s*நூறு|पांच\s*सौ/i.test(transcriptText)) {
          weight = 500;
          weightConfidence = 95;
        } else {
          const bagMatch = text.match(/(\d+)\s*(?:bag|bags|sack|sacks|மூட்டை|மூடை|बोरी|कट्टा)/);
          if (bagMatch) {
            weight = parseInt(bagMatch[1], 10) * 50;
            weightConfidence = 95;
          } else {
            const weightMatch = text.match(/(\d+)\s*(?:kg|kgs|kilo|kilos|kilogram|kilograms|கேஜி|கிலோ|किलो|केजी)?/);
            if (weightMatch && parseInt(weightMatch[1], 10) > 0) {
              weight = parseInt(weightMatch[1], 10);
              weightConfidence = 95;
            }
          }
        }

        const cropList = [
          { name: "Tomato", match: ["tomato", "tomatoes", "thakkali", "tamatar", "தக்காளி", "டொமேட்டோ", "टमाटर"] },
          { name: "Brinjal", match: ["brinjal", "eggplant", "baingan", "kathiri", "katharikai", "கத்திரிக்காய்", "கத்திரி", "बैंगन"] },
          { name: "Onion", match: ["onion", "onions", "vengayam", "venkayam", "pyaz", "pyaaz", "வெங்காயம்", "வெங்காய", "प्याज"] },
          { name: "Banana", match: ["banana", "bananas", "vazhai", "kela", "வாழை", "வாழைப்பழம்", "केला"] },
          { name: "Potato", match: ["potato", "potatoes", "urulai", "aloo", "உருளைக்கிழங்கு", "உருளை", "आलू"] },
          { name: "Paddy", match: ["paddy", "rice", "nellu", "dhan", "chawal", "நெல்", "அரிசி", "धान"] },
          { name: "Cabbage", match: ["cabbage", "muttakose", "முட்டைக்கோஸ்", "पत्ता गोभी"] },
          { name: "Mango", match: ["mango", "mambazham", "மாம்பழம்", "மாங்காய்", "आम"] },
          { name: "Carrot", match: ["carrot", "கேரட்", "गाजर"] }
        ];
        let crop = "Tomato";
        let cropConfidence = 45;
        for (const c of cropList) {
          if (c.match.some((m) => text.includes(m) || transcriptText.includes(m))) {
            crop = c.name;
            cropConfidence = 95;
            break;
          }
        }

        const villageList = [
          { name: "Chittoor", match: ["chittoor", "chittor", "சித்தூர்"] },
          { name: "Melma", match: ["melma", "மேல்மா"] },
          { name: "Athur", match: ["athur", "attur", "ஆத்தூர்"] },
          { name: "Sevoor", match: ["sevoor", "சேவூர்"] },
          { name: "Walajabad", match: ["walajabad", "walajapet", "வாலாஜாபாத்"] },
          { name: "Kancheepuram", match: ["kancheepuram", "kanchipuram", "kanchi", "காஞ்சிபுரம்"] },
          { name: "Vallam", match: ["vallam", "வல்லம்"] },
          { name: "Orikkai", match: ["orikkai", "ஒரிக்காய்"] }
        ];
        let village = "Chittoor";
        let villageConfidence = 45;
        for (const v of villageList) {
          if (v.match.some((m) => text.includes(m) || transcriptText.includes(m))) {
            village = v.name;
            villageConfidence = 92;
            break;
          }
        }

        let destination = "Koyambedu Mandi";
        if (transcriptText.includes("சென்னை") || text.includes("chennai") || transcriptText.includes("கோயம்பேடு")) {
          destination = "Koyambedu Mandi";
        }

        let extractedFarmer = farmerName;
        const nameMatch = transcriptText.match(/(?:my name is|i am|this is|main|naan|en peyar)\s+([A-Za-z]+)/i);
        if (nameMatch && nameMatch[1]) {
          const raw = nameMatch[1].trim();
          if (!["from", "in", "the", "a", "an", "here"].includes(raw.toLowerCase())) {
            extractedFarmer = raw.charAt(0).toUpperCase() + raw.slice(1);
          }
        }

        return {
          id: null,
          transcript: transcriptText,
          extracted: {
            farmer_name: extractedFarmer,
            village: village,
            source_village: village,
            destination: destination,
            destination_village: destination,
            crop: crop,
            weight: weight > 0 ? weight : 400
          },
          confidence: {
            farmer_name: 95,
            village: villageConfidence,
            crop: cropConfidence,
            weight: weightConfidence
          },
          reviewRequired: weight <= 0,
          booking: null
        };
      }

      // If no speech was detected, throw error so UI displays prompt instead of fake data
      throw new Error(err?.message || "No speech detected. Please speak into your microphone and try again.");
    }
  }
};


