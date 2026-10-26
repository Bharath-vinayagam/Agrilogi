import type { AIExtraction, Bid, Driver, FarmerOrder, Recommendation, SavingsPoint } from "@/types";

export const farmerOrders: FarmerOrder[] = [
  {
    id: "KB1024",
    farmerName: "Arumugam",
    phone: "+91 90030 11224",
    village: "Melma",
    crop: "Tomato",
    weightKg: 400,
    status: "Driver Assigned",
    destination: "Koyambedu Mandi",
    individualCost: 3400,
    sharedCost: 1450,
    pickupTime: "Today, 5:30 PM",
    lat: 12.516,
    lng: 79.158,
    clusterId: "CL-0"
  },
  {
    id: "KB1025",
    farmerName: "Meena",
    phone: "+91 94441 22009",
    village: "Athur",
    crop: "Tomato",
    weightKg: 320,
    status: "Cluster Forming",
    destination: "Koyambedu Mandi",
    individualCost: 3100,
    sharedCost: 1320,
    pickupTime: "Today, 5:45 PM",
    lat: 12.550,
    lng: 79.200,
    clusterId: "CL-0"
  },
  {
    id: "KB1026",
    farmerName: "Rafiq",
    phone: "+91 81221 47770",
    village: "Sevoor",
    crop: "Brinjal",
    weightKg: 250,
    status: "Pending",
    destination: "Koyambedu Mandi",
    individualCost: 2600,
    sharedCost: 1180,
    pickupTime: "Today, 6:10 PM",
    lat: 12.520,
    lng: 79.180,
    clusterId: "CL-0"
  }
];

export const drivers: Driver[] = [
  {
    id: "D100",
    name: "Kannan",
    phone: "+91 98844 77882",
    vehicleNumber: "TN 11 AB 4472",
    vehicleType: "Tata Ace",
    licenseNumber: "TN2021007711",
    reliabilityScore: 96
  },
  {
    id: "D101",
    name: "Selvi Logistics",
    phone: "+91 90801 12234",
    vehicleNumber: "TN 22 CD 1932",
    vehicleType: "Mahindra Bolero Pickup",
    licenseNumber: "TN2019034821",
    reliabilityScore: 91
  }
];

export const bids: Bid[] = [
  {
    id: "B801",
    driverName: "Kannan",
    vehicle: "Tata Ace",
    amount: 4350,
    reliabilityScore: 96,
    status: "Leading"
  },
  {
    id: "B802",
    driverName: "Selvi Logistics",
    vehicle: "Bolero Pickup",
    amount: 4620,
    reliabilityScore: 91,
    status: "Open"
  },
  {
    id: "B803",
    driverName: "Velu",
    vehicle: "Ashok Leyland Dost",
    amount: 4890,
    reliabilityScore: 88,
    status: "Open"
  }
];

export const extraction: AIExtraction = {
  transcript: "Naan Arumugam. Melma gramathula irukken. En kitta 400 kilo thakkali irukku.",
  extracted: {
    farmer_name: "Arumugam",
    village: "Melma",
    crop: "Tomato",
    weight: 400
  },
  confidence: {
    farmer_name: 94,
    village: 92,
    crop: 96,
    weight: 97
  }
};

export const recommendation: Recommendation = {
  farmers: 3,
  totalWeightKg: 970,
  truckUtilization: 88,
  estimatedSavings: 5150,
  spoilageRisk: "Medium",
  departureTime: "Today, 5:30 PM"
};

export const savingsTrend: SavingsPoint[] = [
  { label: "Mon", value: 1200 },
  { label: "Tue", value: 2600 },
  { label: "Wed", value: 3900 },
  { label: "Thu", value: 5150 },
  { label: "Fri", value: 6900 }
];

