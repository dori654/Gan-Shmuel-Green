import pytest
import requests
from datetime import datetime
import time

BASE_URL = "http://localhost:5000"  # or 127.0.0.1:5000


@pytest.mark.order(1)
def test_weight_in_and_out_flow():
    truck_id = "T-14263"
    container_id = "C-35434"
    produce = "orange"
    bruto_weight = 12000
    
    # === STEP 0: Register the container ===
    print("\n🛠️  Registering container C-35434 via /batch-weight...")
    response = requests.post(f"{BASE_URL}/batch-weight", files={
        'file': ('containers.csv', 'id,kg\nC-35434,100', 'text/csv')
    })
    assert response.status_code == 201

    # === STEP 1: POST /weight (IN) ===
    print("🟠 [STEP 1] Posting truck IN data...")
    in_payload = {
        "direction": "in",
        "truck": truck_id,
        "containers": [container_id],
        "weight": bruto_weight,
        "produce": produce
    }
    in_response = requests.post(f"{BASE_URL}/weight", json=in_payload)
    print("Status:", in_response.status_code)
    print("Response:", in_response.json())
    assert in_response.status_code == 201
    assert "bruto" in in_response.json()

    # === STEP 2: POST /weight (OUT) ===
    print("🟢 [STEP 2] Posting truck OUT data...")
    out_payload = {
        "direction": "out",
        "truck": truck_id,
        "containers": [container_id],
        "produce": produce
    }
    out_response = requests.post(f"{BASE_URL}/weight", json=out_payload)
    print("Status:", out_response.status_code)
    print("Response:", out_response.json())
    assert out_response.status_code == 201
    assert "neto" in out_response.json()

    # === STEP 3: GET /weight to confirm transaction ===

    print("Waiting briefly before querying /weight...")
    time.sleep(1.5)  # Let DB catch up (just in case)

    print("🔵 [STEP 3] Verifying with GET /weight...")
    now = datetime.now()
    from_ts = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y%m%d%H%M%S")
    to_ts = now.strftime("%Y%m%d%H%M%S")

    get_response = requests.get(f"{BASE_URL}/weight?from={from_ts}&to={to_ts}")
    print("Status:", get_response.status_code)
    assert get_response.status_code == 200
    transactions = get_response.json()

    get_response = requests.get(f"{BASE_URL}/weight?from={from_ts}&to={to_ts}")
    print("Status:", get_response.status_code)
    assert get_response.status_code == 200
    transactions = get_response.json()

    # === STEP 4: Verify truck ID exists ===
    # STEP 4: Verify truck ID exists
    #STEP 4: Verify truck ID exists
    in_found = any(t["direction"] == "in" and t.get("truck") == truck_id for t in transactions)
    out_found = any(t["direction"] == "out" and t.get("truck") == truck_id for t in transactions)
    assert in_found, f"❌ No IN transaction found for truck {truck_id}"
    assert out_found, f"❌ No OUT transaction found for truck {truck_id}"
    in_transactions = [t for t in transactions if t["direction"] == "in" and t.get("truck") == truck_id]
    in_tx_id = in_transactions[0]["id"]

    print(f"✅ Found both IN and OUT transactions for truck {truck_id}")


    # === STEP 5: Validate /unknown shows nothing unexpected ===
    print("[STEP 5] Checking /unknown containers...")
    unknown_response = requests.get(f"{BASE_URL}/unknown")
    print("Status:", unknown_response.status_code)
    print("Response:", unknown_response.json())
    assert unknown_response.status_code == 200

    unknown_containers = unknown_response.json().get("unknown_containers", [])
    assert isinstance(unknown_containers, list)

        # The container we used is registered — should NOT be unknown
    assert container_id not in unknown_containers, f"{container_id} was unexpectedly marked as unknown"


     # === STEP 6: Check /session/<id> ===
    print(f"[STEP 6] Waiting briefly before fetching session details for IN transaction ID {in_tx_id}...")

    MAX_RETRIES = 5
    session_data = None

    for attempt in range(MAX_RETRIES):
        # Let the OUT transaction finalize
        session_response = requests.get(f"{BASE_URL}/session/{in_tx_id}")
        print(f"Attempt {attempt + 1} - Status:", session_response.status_code)
        session_data = session_response.json()
        print("Response:", session_data)

        # Break early if session response contains expected keys
        if session_response.status_code == 200 and "truckTara" in session_data and "neto" in session_data:
            break
    else:
        assert False, f"❌ Expected 'truckTara' and 'neto' in session response after {MAX_RETRIES} retries"

    assert session_data["id"] == in_tx_id
    assert session_data["truck"] == truck_id
    assert session_data["bruto"] == bruto_weight
    assert isinstance(session_data["truckTara"], int)
    assert isinstance(session_data["neto"], int)

    print("✅ Session details validated successfully.")


    #       # === STEP 7: Check /item/<id>?from=...&to=... ===
    # print("[STEP 7] Verifying /item/<id> for container and truck...")

    # item_from = from_ts
    # item_to = to_ts

    # # --- Container Check ---
    # container_item_response = requests.get(
    #     f"{BASE_URL}/item/{container_id}?from={item_from}&to={item_to}"
    # )
    # print(f"Container {container_id} response:", container_item_response.json())
    # assert container_item_response.status_code == 200

    # container_data = container_item_response.json()
    # assert container_data["id"] == container_id
    # assert isinstance(container_data["tara"], (list, int, str)), f"Tara should be list/int/'na', got {type(container_data['tara'])}"
    # assert isinstance(container_data["sessions"], list)
    # assert len(container_data["sessions"]) > 0

    # # --- Truck Check ---
    # truck_item_response = requests.get(
    #     f"{BASE_URL}/item/{truck_id}?from={item_from}&to={item_to}"
    # )
    # print(f"Truck {truck_id} response:", truck_item_response.json())
    # assert truck_item_response.status_code == 200

    # truck_data = truck_item_response.json()
    # assert truck_data["id"] == truck_id
    # assert isinstance(truck_data["tara"], (int, str)), f"Tara should be int/'na', got {type(truck_data['tara'])}"
    # assert isinstance(truck_data["sessions"], list)
    # assert len(truck_data["sessions"]) > 0

    # # --- Non-existent Item Check ---
    # unknown_id = "ID-DOES-NOT-EXIST"
    # unknown_response = requests.get(
    #     f"{BASE_URL}/item/{unknown_id}?from={item_from}&to={item_to}"
    # )
    # print(f"Unknown ID response:", unknown_response.status_code)
    # assert unknown_response.status_code == 404

    # print("✅ /item/<id> endpoint passed all checks.")
