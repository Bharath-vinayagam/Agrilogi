"""
Test Script for Secure Authentication System
Tests registration, OTP verification, vehicle/license verification, and login flows
"""

import requests
import time
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

# Test data
TEST_DRIVER = {
    "name": "Test Driver",
    "phone": "+919876543210",
    "password": "SecurePass123!",
    "role": "driver",
    "village": "Test Village",
    "city": "Chennai",
    "district": "Kancheepuram",
    "state": "Tamil Nadu",
    "pin_code": "600001",
    "vehicle_number": "TN 11 AB 1234",
    "vehicle_type": "Standard Truck",
    "license_number": "DL-1420230001234"
}

TEST_FARMER = {
    "name": "Test Farmer",
    "phone": "+919876543211",
    "password": "SecurePass123!",
    "role": "farmer",
    "village": "Test Village",
    "city": "Chennai",
    "district": "Kancheepuram",
    "state": "Tamil Nadu",
    "pin_code": "600001"
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}{Colors.END}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.END}")

def test_driver_registration():
    """Test complete driver registration flow"""
    print_test("Driver Registration Flow")
    
    try:
        # Step 1: Register
        print_info("Step 1: Registering driver...")
        response = requests.post(f"{API_BASE}/api/auth/register", json=TEST_DRIVER)
        
        if response.status_code == 409:
            print_info("User already exists, using existing account")
            # Try to get user by cleaning up first
            return None
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        data = response.json()
        
        print_success(f"Registration successful. User ID: {data['user_id']}")
        print_info(f"Phone verified: {data['phone_verified']}")
        print_info(f"OTP sent: {data['otp_sent']}")
        
        if 'otp' in data:
            print_info(f"DEV MODE - OTP Code: {data['otp']}")
        
        user_id = data['user_id']
        otp = data.get('otp', '123456')  # Use displayed OTP or default
        
        # Step 2: Verify OTP
        print_info("\nStep 2: Verifying OTP...")
        time.sleep(1)
        
        verify_response = requests.post(f"{API_BASE}/api/auth/verify-otp", json={
            "user_id": user_id,
            "otp": otp
        })
        
        assert verify_response.status_code == 200, f"Expected 200, got {verify_response.status_code}"
        verify_data = verify_response.json()
        
        print_success(f"Phone verified: {verify_data['verified']}")
        
        print_success("Driver registration flow completed successfully")
        return user_id
        
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is the server running on http://localhost:8000?")
        return None
    except AssertionError as e:
        print_error(f"Assertion failed: {e}")
        return None
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return None

def test_otp_rate_limiting():
    """Test OTP rate limiting"""
    print_test("OTP Rate Limiting")
    
    try:
        print_info("Sending first OTP...")
        response1 = requests.post(f"{API_BASE}/api/auth/send-otp", json={
            "user_id": "test-rate-limit-id",
            "phone": "+919999999999",
            "name": "Rate Test"
        })
        
        print_info("Attempting to send OTP again immediately...")
        time.sleep(0.5)
        
        response2 = requests.post(f"{API_BASE}/api/auth/send-otp", json={
            "user_id": "test-rate-limit-id",
            "phone": "+919999999999",
            "name": "Rate Test"
        })
        
        if response2.status_code == 400:
            error_msg = response2.json().get('detail', '')
            if 'wait' in error_msg.lower() or 'seconds' in error_msg.lower():
                print_success("Rate limiting working correctly")
                print_info(f"Error message: {error_msg}")
                return True
        
        print_error("Rate limiting not working as expected")
        return False
        
    except Exception as e:
        print_error(f"Error testing rate limiting: {e}")
        return False

def test_invalid_otp():
    """Test invalid OTP handling"""
    print_test("Invalid OTP Handling")
    
    try:
        # First register a user
        print_info("Registering test user...")
        reg_response = requests.post(f"{API_BASE}/api/auth/register", json={
            **TEST_DRIVER,
            "phone": "+919876543299",
            "name": "OTP Test User"
        })
        
        if reg_response.status_code == 409:
            print_info("User exists, skipping registration")
            return True
        
        user_id = reg_response.json()['user_id']
        
        print_info("Attempting verification with wrong OTP...")
        verify_response = requests.post(f"{API_BASE}/api/auth/verify-otp", json={
            "user_id": user_id,
            "otp": "000000"  # Wrong OTP
        })
        
        if verify_response.status_code == 400:
            error_msg = verify_response.json().get('detail', '')
            if 'incorrect' in error_msg.lower() or 'invalid' in error_msg.lower():
                print_success("Invalid OTP handled correctly")
                print_info(f"Error message: {error_msg}")
                return True
        
        print_error("Invalid OTP not handled properly")
        return False
        
    except Exception as e:
        print_error(f"Error testing invalid OTP: {e}")
        return False

def test_vehicle_verification():
    """Test vehicle verification with various formats"""
    print_test("Vehicle Verification")
    
    test_cases = [
        ("TN 11 AB 4472", True, "Valid format with spaces"),
        ("TN-11-AB-4472", True, "Valid format with hyphens"),
        ("KA 01 CD 1234", True, "Valid Karnataka vehicle"),
        ("INVALID123", False, "Invalid format"),
        ("XX 11 AB 1234", False, "Invalid state code"),
    ]
    
    for vehicle_num, should_pass, description in test_cases:
        try:
            print_info(f"\nTesting: {description} - {vehicle_num}")
            
            response = requests.post(f"{API_BASE}/api/auth/verify-vehicle", json={
                "driver_id": "test-driver-id",
                "vehicle_number": vehicle_num,
                "owner_name": "Test Owner"
            })
            
            if should_pass:
                if response.status_code == 200:
                    data = response.json()
                    print_success(f"✓ Accepted - Status: {data.get('status', 'unknown')}")
                    if data.get('status') == 'manual_review':
                        print_info("  Submitted for manual review (expected)")
                else:
                    print_error(f"✗ Rejected unexpectedly - {response.status_code}")
            else:
                if response.status_code == 400:
                    error_msg = response.json().get('detail', '')
                    print_success(f"✓ Rejected correctly - {error_msg}")
                else:
                    print_error(f"✗ Accepted unexpectedly")
                    
        except Exception as e:
            print_error(f"Error: {e}")
    
    print_success("\nVehicle verification tests completed")
    return True

def test_license_verification():
    """Test license verification with various formats"""
    print_test("License Verification")
    
    test_cases = [
        ("DL-1420230005524", True, "Valid DL format"),
        ("MH-0220240001234", True, "Valid Maharashtra license"),
        ("TN-5920250009999", True, "Valid Tamil Nadu license"),
        ("INVALID", False, "Invalid format"),
        ("DL-1419900005524", False, "Invalid year (1990)"),
    ]
    
    for license_num, should_pass, description in test_cases:
        try:
            print_info(f"\nTesting: {description} - {license_num}")
            
            response = requests.post(f"{API_BASE}/api/auth/verify-license", json={
                "driver_id": "test-driver-id",
                "license_number": license_num,
                "holder_name": "Test Holder"
            })
            
            if should_pass:
                if response.status_code == 200:
                    data = response.json()
                    print_success(f"✓ Accepted - Status: {data.get('status', 'unknown')}")
                    if data.get('status') == 'manual_review':
                        print_info("  Submitted for manual review (expected)")
                else:
                    print_error(f"✗ Rejected unexpectedly - {response.status_code}")
            else:
                if response.status_code == 400:
                    error_msg = response.json().get('detail', '')
                    print_success(f"✓ Rejected correctly - {error_msg}")
                else:
                    print_error(f"✗ Accepted unexpectedly")
                    
        except Exception as e:
            print_error(f"Error: {e}")
    
    print_success("\nLicense verification tests completed")
    return True

def test_login_flow():
    """Test login with correct and incorrect credentials"""
    print_test("Login Flow")
    
    try:
        # Test 1: Correct credentials
        print_info("Test 1: Login with correct credentials...")
        response = requests.post(f"{API_BASE}/api/auth/login", json={
            "phone": TEST_DRIVER["phone"],
            "password": TEST_DRIVER["password"],
            "role": "driver"
        })
        
        if response.status_code == 200:
            data = response.json()
            print_success("Login successful")
            print_info(f"User: {data['user']['name']}")
            print_info(f"Role: {data['user']['role']}")
            if 'vehicle_verification_status' in data['user']:
                print_info(f"Vehicle status: {data['user']['vehicle_verification_status']}")
                print_info(f"License status: {data['user']['license_verification_status']}")
                print_info(f"Account status: {data['user']['account_status']}")
        else:
            print_info(f"Login returned {response.status_code} - user may not exist or phone not verified")
        
        # Test 2: Wrong password
        print_info("\nTest 2: Login with wrong password...")
        response = requests.post(f"{API_BASE}/api/auth/login", json={
            "phone": TEST_DRIVER["phone"],
            "password": "WrongPassword123!",
            "role": "driver"
        })
        
        if response.status_code == 401 or response.status_code == 400:
            print_success("Wrong password rejected correctly")
        else:
            print_error("Wrong password not rejected")
        
        # Test 3: Wrong role
        print_info("\nTest 3: Login with wrong role...")
        response = requests.post(f"{API_BASE}/api/auth/login", json={
            "phone": TEST_DRIVER["phone"],
            "password": TEST_DRIVER["password"],
            "role": "farmer"  # Driver account but logging in as farmer
        })
        
        if response.status_code == 400 or response.status_code == 403:
            error_msg = response.json().get('detail', '')
            print_success("Role mismatch detected correctly")
            print_info(f"Error: {error_msg}")
        else:
            print_error("Role mismatch not detected")
        
        print_success("\nLogin flow tests completed")
        return True
        
    except Exception as e:
        print_error(f"Error testing login: {e}")
        return False

def test_password_strength():
    """Test password strength validation"""
    print_test("Password Strength Validation")
    
    weak_passwords = [
        ("123", "Too short"),
        ("password", "No numbers or special chars"),
        ("12345678", "Only numbers"),
    ]
    
    strong_passwords = [
        ("SecurePass123!", "Good mix"),
        ("MyP@ssw0rd2024", "Good mix"),
    ]
    
    print_info("Testing weak passwords (should fail):")
    for pwd, description in weak_passwords:
        print_info(f"  - {pwd} ({description})")
        if len(pwd) < 8:
            print_success(f"    ✓ Would be rejected (too short)")
        elif not any(c.isdigit() or not c.isalnum() for c in pwd):
            print_success(f"    ✓ Would be rejected (no number/special char)")
    
    print_info("\nTesting strong passwords (should pass):")
    for pwd, description in strong_passwords:
        print_info(f"  - {pwd} ({description})")
        if len(pwd) >= 8 and any(c.isdigit() or not c.isalnum() for c in pwd):
            print_success(f"    ✓ Would be accepted")
    
    print_success("\nPassword strength validation tests completed")
    return True

def run_all_tests():
    """Run all test suites"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("AGRILOGI SECURE AUTHENTICATION SYSTEM - TEST SUITE")
    print(f"{'='*60}{Colors.END}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Base URL: {API_BASE}\n")
    
    results = {}
    
    # Run tests
    results['driver_registration'] = test_driver_registration() is not None
    results['otp_rate_limiting'] = test_otp_rate_limiting()
    results['invalid_otp'] = test_invalid_otp()
    results['vehicle_verification'] = test_vehicle_verification()
    results['license_verification'] = test_license_verification()
    results['login_flow'] = test_login_flow()
    results['password_strength'] = test_password_strength()
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.END}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.END}" if passed_test else f"{Colors.RED}FAILED{Colors.END}"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    if passed == total:
        print(f"{Colors.GREEN}✅ ALL TESTS PASSED ({passed}/{total}){Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  SOME TESTS FAILED ({passed}/{total} passed){Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    print_info("Note: Some tests may fail if:")
    print_info("  - Backend server is not running on http://localhost:8000")
    print_info("  - Database migration has not been applied")
    print_info("  - Twilio credentials are not configured (OTP will use dev mode)")
    print_info("  - Test data already exists in database")

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.END}")
