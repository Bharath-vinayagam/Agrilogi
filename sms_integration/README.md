# SMS Integration for Agrilogi

**Purpose:** Automated SMS notifications for clustering and bidding events  
**Provider:** Twilio SMS API  
**Status:** Production Ready

---

## 📱 SMS Scenarios

### Scenario 1: Cluster Created → Notify All Drivers
**Trigger:** After clustering algorithm runs  
**Recipients:** All active drivers  
**Message:** New bundles available for bidding

### Scenario 2: Bidding Closed → Notify Winner & Farmers
**Trigger:** When lowest bid wins a cluster  
**Recipients:** Winning driver + all farmers in cluster  
**Messages:**
- Driver: Congratulations, you won the bid
- Farmers: Your order has been assigned to driver

---

## 🗂️ File Structure

```
sms_integration/
├── README.md                    # This file
├── sms_triggers.py              # Main SMS trigger logic
├── message_templates.py         # SMS message templates
├── driver_notifications.py      # Driver SMS functions
├── farmer_notifications.py      # Farmer SMS functions
├── test_sms.py                  # Testing script
├── requirements.txt             # Dependencies
└── TESTING_GUIDE.md            # How to test SMS
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd sms_integration
pip install -r requirements.txt
```

### 2. Configure Twilio
```bash
# Add to backend/.env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

### 3. Test SMS System
```bash
python test_sms.py
```

---

## 📝 Usage

### Trigger SMS on Clustering:
```python
from sms_integration.sms_triggers import notify_drivers_cluster_created

# After clustering runs
cluster_ids = ["CL-001", "CL-002"]
notify_drivers_cluster_created(cluster_ids)
```

### Trigger SMS on Bid Win:
```python
from sms_integration.sms_triggers import notify_bid_winner

# After bid is closed
notify_bid_winner(
    cluster_id="CL-001",
    driver_name="Kumar",
    driver_phone="+919876543210",
    bid_amount=4500
)
```

---

## 🔧 Integration Points

### 1. Clustering Endpoint
**File:** `backend/routes/admin.py`  
**Endpoint:** `POST /api/admin/trigger-clustering`  
**Add after clustering:** Call `notify_drivers_cluster_created()`

### 2. Bid Closing Endpoint
**File:** `backend/routes/slot_bids.py`  
**Endpoint:** `POST /api/bids/cluster/{cluster_id}/close`  
**Add after winner selection:** Call `notify_bid_winner()`

---

## 📊 SMS Logs

All SMS are logged to `notifications` table:
```sql
SELECT * FROM notifications 
WHERE channel = 'sms' 
ORDER BY created_at DESC;
```

---

## 🧪 Testing

See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for detailed testing instructions.

Quick test:
```bash
python test_sms.py --scenario cluster_created
python test_sms.py --scenario bid_winner
```

---

## 📈 Monitoring

Check SMS delivery status:
```python
from sms_integration.sms_triggers import get_sms_stats

stats = get_sms_stats(days=7)
print(f"Sent: {stats['sent']}")
print(f"Failed: {stats['failed']}")
print(f"Queued: {stats['queued']}")
```

---

## 🔐 Security

- ✅ Phone numbers are validated before sending
- ✅ Twilio credentials stored in environment variables
- ✅ All SMS logged to database for audit
- ✅ Rate limiting to prevent spam
- ✅ Fallback to database logging if Twilio unavailable

---

## 💰 Cost Estimation

**Twilio Pricing (India):**
- SMS to India: ~₹0.50 - ₹1.00 per SMS
- Trial account: 500 free SMS

**Expected Usage:**
- Clustering: 1-5 SMS per cluster (all drivers)
- Bid closed: 2-10 SMS per cluster (winner + farmers)
- Monthly estimate: 500-1000 SMS (₹500-₹1000/month)

---

## 🆘 Support

**Issues?**
1. Check Twilio credentials in `.env`
2. Review SMS logs in `notifications` table
3. Test with `python test_sms.py`
4. Check console logs for errors

**Contact:** Support team for Twilio account access
