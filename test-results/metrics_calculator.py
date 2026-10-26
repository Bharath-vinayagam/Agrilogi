#!/usr/bin/env python3
"""
Metrics Calculator for Agrilogi
Calculates actual business metrics from real database data
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any
import statistics

BASE_URL = "http://localhost:8000"

class MetricsCalculator:
    def __init__(self):
        self.metrics = {}
        self.raw_data = {}
        self.evidence = {}
        
    def fetch_data(self):
        """Fetch all necessary data from API"""
        print("Fetching data from backend...")
        
        try:
            # Get all bookings
            response = requests.get(f"{BASE_URL}/api/bookings", timeout=10)
            self.raw_data['bookings'] = response.json() if response.status_code == 200 else []
            print(f"  [OK] Fetched {len(self.raw_data['bookings'])} bookings")
            
            # Get all drivers
            response = requests.get(f"{BASE_URL}/api/drivers", timeout=10)
            self.raw_data['drivers'] = response.json() if response.status_code == 200 else []
            print(f"  [OK] Fetched {len(self.raw_data['drivers'])} drivers")
            
            # Get all bids
            response = requests.get(f"{BASE_URL}/api/auction/bids", timeout=10)
            self.raw_data['bids'] = response.json() if response.status_code == 200 else []
            print(f"  [OK] Fetched {len(self.raw_data['bids'])} bids")
            
            # Get admin snapshot
            response = requests.get(f"{BASE_URL}/api/admin/snapshot", timeout=10)
            self.raw_data['snapshot'] = response.json() if response.status_code == 200 else {}
            print(f"  [OK] Fetched admin snapshot")
            
            return True
        except Exception as e:
            print(f"  [ERROR] Error fetching data: {e}")
            return False
    
    def calculate_metric_1_cost_savings(self):
        """
        METRIC 1: Total Cost Savings
        Formula: Sum of (individual_cost - shared_cost) for all orders where both costs exist
        """
        print("\n### METRIC 1: Total Cost Savings")
        
        bookings = self.raw_data.get('bookings', [])
        
        total_individual_cost = 0
        total_shared_cost = 0
        total_savings = 0
        orders_with_savings = []
        
        for booking in bookings:
            individual = booking.get('individual_cost', 0) or 0
            shared = booking.get('shared_cost', 0) or 0
            
            if individual > 0:
                total_individual_cost += individual
                total_shared_cost += shared
                
                if shared > 0 and shared < individual:
                    savings = individual - shared
                    total_savings += savings
                    orders_with_savings.append({
                        'id': booking.get('id'),
                        'farmer': booking.get('farmer_name'),
                        'individual': individual,
                        'shared': shared,
                        'savings': savings
                    })
        
        self.metrics['total_cost_savings'] = {
            'name': 'Total Cost Savings',
            'formula': 'Sum of (individual_cost - shared_cost) for all orders',
            'baseline': total_individual_cost,
            'optimized': total_shared_cost,
            'actual_result': total_savings,
            'unit': 'INR (₹)',
            'sample_size': len(orders_with_savings),
            'data_source': 'orders table via /api/bookings',
            'measurement_method': 'MEASURED - Direct database query',
            'evidence': f"{len(orders_with_savings)} orders with cost data",
        }
        
        self.evidence['cost_savings_detail'] = orders_with_savings[:10]  # Top 10 for report
        
        print(f"  Baseline (Individual): ₹{total_individual_cost:,}")
        print(f"  Optimized (Shared): ₹{total_shared_cost:,}")
        print(f"  Total Savings: ₹{total_savings:,}")
        print(f"  Sample Size: {len(orders_with_savings)} orders")
        
        return total_savings
    
    def calculate_metric_2_cost_reduction_percentage(self):
        """
        METRIC 2: Average Cost Reduction Percentage
        Formula: Average of ((individual_cost - shared_cost) / individual_cost * 100) for orders with both costs
        """
        print("\n### METRIC 2: Average Cost Reduction Percentage")
        
        bookings = self.raw_data.get('bookings', [])
        
        reduction_percentages = []
        
        for booking in bookings:
            individual = booking.get('individual_cost', 0) or 0
            shared = booking.get('shared_cost', 0) or 0
            
            if individual > 0 and shared > 0 and shared < individual:
                reduction_pct = ((individual - shared) / individual) * 100
                reduction_percentages.append(reduction_pct)
        
        if reduction_percentages:
            avg_reduction = statistics.mean(reduction_percentages)
            median_reduction = statistics.median(reduction_percentages)
            min_reduction = min(reduction_percentages)
            max_reduction = max(reduction_percentages)
        else:
            avg_reduction = 0
            median_reduction = 0
            min_reduction = 0
            max_reduction = 0
        
        self.metrics['cost_reduction_percentage'] = {
            'name': 'Average Cost Reduction Percentage',
            'formula': '((individual_cost - shared_cost) / individual_cost) × 100',
            'baseline': 100.0,
            'actual_result': round(avg_reduction, 2),
            'unit': 'Percentage (%)',
            'sample_size': len(reduction_percentages),
            'data_source': 'orders table via /api/bookings',
            'measurement_method': 'CALCULATED - Statistical mean of individual reductions',
            'evidence': f"Min: {min_reduction:.1f}%, Max: {max_reduction:.1f}%, Median: {median_reduction:.1f}%",
        }
        
        print(f"  Average: {avg_reduction:.2f}%")
        print(f"  Median: {median_reduction:.2f}%")
        print(f"  Range: {min_reduction:.1f}% - {max_reduction:.1f}%")
        print(f"  Sample Size: {len(reduction_percentages)} orders")
        
        return avg_reduction
    
    def calculate_metric_3_api_success_rate(self):
        """
        METRIC 3: API Success Rate
        Tests all major endpoints and calculates success rate
        """
        print("\n### METRIC 3: API Endpoint Success Rate")
        
        endpoints = [
            ('GET', '/health'),
            ('GET', '/api/bookings'),
            ('GET', '/api/drivers'),
            ('GET', '/api/admin/snapshot'),
        ]
        
        successful = 0
        failed = 0
        results = []
        
        for method, endpoint in endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=3)
                    
                if response.status_code in [200, 201]:
                    successful += 1
                    results.append({'endpoint': endpoint, 'status': 'SUCCESS', 'code': response.status_code})
                else:
                    failed += 1
                    results.append({'endpoint': endpoint, 'status': 'FAIL', 'code': response.status_code})
            except Exception as e:
                failed += 1
                results.append({'endpoint': endpoint, 'status': 'ERROR', 'error': str(e)})
        
        total = successful + failed
        success_rate = (successful / total * 100) if total > 0 else 0
        
        self.metrics['api_success_rate'] = {
            'name': 'API Endpoint Success Rate',
            'formula': '(Successful requests / Total requests) × 100',
            'baseline': 100.0,
            'actual_result': round(success_rate, 2),
            'unit': 'Percentage (%)',
            'sample_size': total,
            'data_source': 'Live API testing',
            'measurement_method': 'MEASURED - Direct HTTP requests to all endpoints',
            'evidence': f"{successful} successful, {failed} failed out of {total}",
        }
        
        self.evidence['api_test_results'] = results
        
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Successful: {successful}/{total}")
        print(f"  Failed: {failed}/{total}")
        
        return success_rate
    
    def calculate_metric_4_booking_completion_rate(self):
        """
        METRIC 4: Booking Completion Rate
        Percentage of bookings that reached 'Completed' status
        """
        print("\n### METRIC 4: Booking Completion Rate")
        
        bookings = self.raw_data.get('bookings', [])
        
        status_counts = {}
        for booking in bookings:
            status = booking.get('status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        completed = status_counts.get('Completed', 0)
        total = len(bookings)
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        self.metrics['booking_completion_rate'] = {
            'name': 'Booking Completion Rate',
            'formula': '(Completed bookings / Total bookings) × 100',
            'baseline': 100.0,
            'actual_result': round(completion_rate, 2),
            'unit': 'Percentage (%)',
            'sample_size': total,
            'data_source': 'orders table via /api/bookings',
            'measurement_method': 'CALCULATED - Status field analysis',
            'evidence': f"Status breakdown: {status_counts}",
        }
        
        print(f"  Completion Rate: {completion_rate:.2f}%")
        print(f"  Completed: {completed}/{total}")
        print(f"  Status Breakdown: {status_counts}")
        
        return completion_rate
    
    def calculate_metric_5_avg_weight_per_booking(self):
        """
        METRIC 5: Average Weight Per Booking
        Measures typical shipment size
        """
        print("\n### METRIC 5: Average Weight Per Booking")
        
        bookings = self.raw_data.get('bookings', [])
        
        weights = []
        for booking in bookings:
            weight = booking.get('weight_kg', 0) or 0
            if weight > 0:
                weights.append(weight)
        
        if weights:
            avg_weight = statistics.mean(weights)
            median_weight = statistics.median(weights)
            total_weight = sum(weights)
            min_weight = min(weights)
            max_weight = max(weights)
        else:
            avg_weight = 0
            median_weight = 0
            total_weight = 0
            min_weight = 0
            max_weight = 0
        
        self.metrics['avg_weight_per_booking'] = {
            'name': 'Average Weight Per Booking',
            'formula': 'Mean of weight_kg across all bookings',
            'baseline': None,
            'actual_result': round(avg_weight, 2),
            'unit': 'Kilograms (kg)',
            'sample_size': len(weights),
            'data_source': 'orders table via /api/bookings',
            'measurement_method': 'CALCULATED - Statistical mean',
            'evidence': f"Total: {total_weight:,}kg, Range: {min_weight}-{max_weight}kg, Median: {median_weight}kg",
        }
        
        print(f"  Average: {avg_weight:.2f} kg")
        print(f"  Median: {median_weight:.2f} kg")
        print(f"  Total Weight: {total_weight:,} kg")
        print(f"  Range: {min_weight} - {max_weight} kg")
        
        return avg_weight
    
    def calculate_metric_6_driver_utilization(self):
        """
        METRIC 6: Driver Utilization Rate
        Percentage of drivers with at least one assigned order
        """
        print("\n### METRIC 6: Driver Utilization Rate")
        
        bookings = self.raw_data.get('bookings', [])
        drivers = self.raw_data.get('drivers', [])
        
        assigned_drivers = set()
        for booking in bookings:
            driver = booking.get('assigned_driver')
            if driver:
                assigned_drivers.add(driver)
        
        total_drivers = len(drivers)
        active_drivers = len(assigned_drivers)
        
        utilization_rate = (active_drivers / total_drivers * 100) if total_drivers > 0 else 0
        
        self.metrics['driver_utilization'] = {
            'name': 'Driver Utilization Rate',
            'formula': '(Drivers with assignments / Total drivers) × 100',
            'baseline': 100.0,
            'actual_result': round(utilization_rate, 2),
            'unit': 'Percentage (%)',
            'sample_size': total_drivers,
            'data_source': 'drivers and orders tables',
            'measurement_method': 'CALCULATED - Set intersection of assigned drivers',
            'evidence': f"{active_drivers} active out of {total_drivers} total drivers",
        }
        
        print(f"  Utilization Rate: {utilization_rate:.2f}%")
        print(f"  Active Drivers: {active_drivers}/{total_drivers}")
        
        return utilization_rate
    
    def calculate_metric_7_avg_bids_per_order(self):
        """
        METRIC 7: Average Bids Per Order
        Measures marketplace competition
        """
        print("\n### METRIC 7: Average Bids Per Order")
        
        bids = self.raw_data.get('bids', [])
        
        # Group bids by order_id
        order_bids = {}
        for bid in bids:
            order_id = bid.get('order_id')
            if order_id:
                if order_id not in order_bids:
                    order_bids[order_id] = []
                order_bids[order_id].append(bid)
        
        bid_counts = [len(bids) for bids in order_bids.values()]
        
        if bid_counts:
            avg_bids = statistics.mean(bid_counts)
            max_bids = max(bid_counts)
            min_bids = min(bid_counts)
        else:
            avg_bids = 0
            max_bids = 0
            min_bids = 0
        
        self.metrics['avg_bids_per_order'] = {
            'name': 'Average Bids Per Order',
            'formula': 'Mean number of bids per order',
            'baseline': None,
            'actual_result': round(avg_bids, 2),
            'unit': 'Bids per order',
            'sample_size': len(order_bids),
            'data_source': 'bids table via /api/auction/bids',
            'measurement_method': 'CALCULATED - Grouped count and mean',
            'evidence': f"Range: {min_bids}-{max_bids} bids, {len(bids)} total bids for {len(order_bids)} orders",
        }
        
        print(f"  Average: {avg_bids:.2f} bids per order")
        print(f"  Range: {min_bids} - {max_bids} bids")
        print(f"  Total Orders with Bids: {len(order_bids)}")
        
        return avg_bids
    
    def calculate_all_metrics(self):
        """Calculate all metrics"""
        print("="*80)
        print("METRICS CALCULATION")
        print("="*80)
        
        if not self.fetch_data():
            print("Failed to fetch data. Cannot calculate metrics.")
            return False
        
        self.calculate_metric_1_cost_savings()
        self.calculate_metric_2_cost_reduction_percentage()
        self.calculate_metric_3_api_success_rate()
        self.calculate_metric_4_booking_completion_rate()
        self.calculate_metric_5_avg_weight_per_booking()
        self.calculate_metric_6_driver_utilization()
        self.calculate_metric_7_avg_bids_per_order()
        
        return True
    
    def save_results(self):
        """Save metrics to JSON file"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_metrics': len(self.metrics),
                'data_sources': ['Supabase Database', 'Live API Testing'],
                'measurement_window': 'All historical data',
            },
            'metrics': self.metrics,
            'evidence': self.evidence,
            'raw_data_counts': {
                'bookings': len(self.raw_data.get('bookings', [])),
                'drivers': len(self.raw_data.get('drivers', [])),
                'bids': len(self.raw_data.get('bids', [])),
            }
        }
        
        with open('metrics_results.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print("\n" + "="*80)
        print("METRICS SUMMARY")
        print("="*80)
        print(f"Total Metrics Calculated: {len(self.metrics)}")
        for metric_key, metric in self.metrics.items():
            print(f"\n{metric['name']}:")
            print(f"  Result: {metric['actual_result']} {metric['unit']}")
            print(f"  Sample Size: {metric['sample_size']}")
            print(f"  Method: {metric['measurement_method']}")
        
        print(f"\n[OK] Results saved to metrics_results.json")

if __name__ == "__main__":
    calculator = MetricsCalculator()
    if calculator.calculate_all_metrics():
        calculator.save_results()
    else:
        print("Metrics calculation failed")
        exit(1)
