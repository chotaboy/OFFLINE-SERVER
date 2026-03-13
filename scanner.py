import cv2
import firebase_admin
from firebase_admin import credentials, db
import json
import os
import requests

# 🔹 ESP32 Camera Stream URL
stream_url = "http://10.169.98.44/stream"

# 🔹 Firebase Setup
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://op-gh-a31ef-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

queue_ref = db.reference("queue")

print("✅ QR Scanner Started... Press ESC to exit")

# 🔹 Start Camera
cap = cv2.VideoCapture(stream_url)
detector = cv2.QRCodeDetector()

last_data = ""

# 🔹 Check Internet
def is_online():
    try:
        requests.get("https://google.com", timeout=3)
        return True
    except:
        return False

# 🔹 Save Offline
def save_offline(data):

    file = "offline_queue.json"

    if os.path.exists(file):
        with open(file, "r") as f:
            q = json.load(f)
    else:
        q = []

    q.append(data)

    with open(file, "w") as f:
        json.dump(q, f)

# 🔹 Sync Offline Data
def sync_offline():

    file = "offline_queue.json"

    if not os.path.exists(file):
        return

    with open(file, "r") as f:
        q = json.load(f)

    for item in q:
        queue_ref.child(str(item["token"])).set(item)

    os.remove(file)

    print("✅ Offline queue synced to Firebase")

# 🔹 Generate Token
def generate_token():

    queue_data = queue_ref.get()

    tokens = []

    if not queue_data:
        return 1

    if isinstance(queue_data, dict):
        for item in queue_data.values():
            if item and "token" in item:
                tokens.append(item["token"])

    if isinstance(queue_data, list):
        for item in queue_data:
            if item and "token" in item:
                tokens.append(item["token"])

    return max(tokens) + 1 if tokens else 1


# 🔹 Main Loop
while True:

    ret, frame = cap.read()

    if not ret:
        print("❌ Failed to get frame from ESP32")
        break

    data, bbox, _ = detector.detectAndDecode(frame)

    if data and data != last_data:

        print("🔹 QR Detected:", data)

        last_data = data

        new_token = generate_token()

        patient_data = {
            "patientId": data,
            "token": new_token,
            "status": "waiting"
        }

        if is_online():

            queue_ref.child(str(new_token)).set(patient_data)

            sync_offline()

            print("✅ Patient Added Online. Token:", new_token)

        else:

            save_offline(patient_data)

            print("📴 Saved Offline. Token:", new_token)

    cv2.imshow("ESP32 Hospital QR Scanner", frame)

    if cv2.waitKey(1) == 27:  # ESC
        break


cap.release()
cv2.destroyAllWindows()

print("🔴 Scanner Stopped")