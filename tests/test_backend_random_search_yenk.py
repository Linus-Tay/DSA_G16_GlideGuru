import random
import json
import traceback
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))

from glideguru.algorithms import yen_k_paths
from app import GD

DATA_PATH = BASE_DIR.parent / "data" / "airline_routes_with_price.json"


with open(DATA_PATH, 'r', encoding='utf-8') as f:
    airport_data = json.load(f)
# airport_data = {
#     "AAA": {"iata": "AAA", "name": "Anaa Airport"},
#     "AAD": {"iata": "AAD", "name": "Adado Airport"}
#     "AAE": {"iata": "AAE", "name": "Annaba"},
#     "AAL": {"iata": "AAL", "name": "Aalborg"},
#     "ABQ": {"iata": "ABQ", "name": "Albuquerque International Sunport"}
# }

# A list of some carriers from your dataset to randomize
available_carriers = ["VT", "AH", "D8", "SK", "KL", "FR", "AA", "DL", "WN"]

def backend_search_api(origin, destination, max_connections, allowed_airlines):
    """
    NOW CALLING THE REAL ENGINE
    """
    # Define the weight function (e.g., price)
    weight_func = lambda edge: float(edge.price)
    
    # Call your actual Yen's K-Shortest Paths algorithm
    # We use k=5 to see if it can find multiple routes
    results = yen_k_paths(
        GD, 
        origin, 
        destination, 
        weight_func, 
        k=5, 
        blocked=set(),
        max_hops=max_connections, 
        allowed=set(allowed_airlines) if allowed_airlines else None
    )
    
    return {"status": "success", "flights_found": len(results)}

def run_randomized_backend_tests(data, num_tests=10):
    airports = list(data.keys())
    failed_cases = []

    print(f"--- Starting {num_tests} Random Backend Tests ---")

    for i in range(num_tests):
        # 2. Pick random origin and destination
        origin = random.choice(airports)
        dest = random.choice(airports)
        while dest == origin:
            dest = random.choice(airports)

        # 3. Randomize the parameters that "matter"
        max_connections = random.choice([0, 1, 2, 3])
        
        # Randomly decide to restrict airlines or allow all (empty list)
        restrict_airlines = random.choice([True, False])
        if restrict_airlines:
            allowed_airlines = random.sample(available_carriers, k=random.randint(1, 4))
        else:
            allowed_airlines = []

        # 4. Define the exact combo being tested
        combo = {
            "test_id": i + 1,
            "origin": origin,
            "destination": dest,
            "max_connections": max_connections,
            "allowed_airlines": allowed_airlines
        }

        # 5. Execute test and catch failures for backtracking
        # 5. Execute test and catch failures for backtracking
        try:
            result = backend_search_api(
                origin=combo["origin"],
                destination=combo["destination"],
                max_connections=combo["max_connections"],
                allowed_airlines=combo["allowed_airlines"]
            )
            
            # You can add assertions here to test the result logic
            assert result["status"] == "success", "Backend returned a non-success status."
            
            print(f"✅ Test {combo['test_id']} Passed: {origin} -> {dest} (Max Conn: {max_connections})")
            
        except Exception as e:
            # Backtrack: Save the exact state of the combo that caused the crash
            combo["error_message"] = str(e)
            failed_cases.append(combo)
            print(f"❌ Test {combo['test_id']} Failed! Combo logged.")

    # 6. Report failures
    print("\n--- Test Run Complete ---")
    if not failed_cases:
        print("All tests passed successfully!")
    else:
        print(f"Found {len(failed_cases)} failed test cases. Backtrack data below:")
        print(json.dumps(failed_cases, indent=4))

# Run the tests
run_randomized_backend_tests(airport_data, num_tests=10)