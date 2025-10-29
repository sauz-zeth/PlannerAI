import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("🧪 Testing AI-Planner Backend...")
    
    # 1. Health check
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Health: {response.status_code} - {response.json()}")
    except:
        print("❌ Health: Server not running")
        return
    
    # 2. Text scheduling
    test_data = {
        "text": "тестовая встреча сегодня в 15:00",
        "user_id": "test_user_123", 
        "calendar_type": "apple"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/schedule", json=test_data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Text Schedule: {result['message']}")
            print(f"   Event: {result['title']} at {result['scheduled_time']}")
        else:
            print(f"❌ Text Schedule: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Text Schedule Error: {e}")
    
    # 3. Get events
    try:
        response = requests.get(f"{BASE_URL}/v1/events/test_user_123", timeout=5)
        if response.status_code == 200:
            events = response.json()
            print(f"✅ Get Events: Found {len(events.get('events', []))} events")
        else:
            print(f"❌ Get Events: {response.status_code}")
    except Exception as e:
        print(f"❌ Get Events Error: {e}")

if __name__ == "__main__":
    test_all()