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

def backend_search_api(origin, destination, max_connections, allowed_airlines, mode):
    """
    TESTING ALL MODES: Cheapest, Fastest, Shortest, Fewest Connections
    """
    # 1. Map the 'mode' to the correct weight function
    if mode == "Cheapest":
        weight_func = lambda edge: float(edge.price)
    elif mode == "Fastest":
        weight_func = lambda edge: float(edge.minutes) 
    elif mode == "Shortest":
        weight_func = lambda edge: float(edge.km) 
    elif mode == "Fewest Connections":
        weight_func = lambda edge: 1 # Every hop counts as '1' to minimize total count
    else:
        weight_func = lambda edge: float(edge.price) # Default

    # 2. Call the real engine
    try:
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
    except Exception as e:
        # Re-raise so the test harness catches it
        raise e

def run_randomized_backend_tests(data, num_tests=10):
    airports = list(data.keys())
    modes = ["Cheapest", "Fastest", "Shortest", "Fewest Connections"]
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
        selected_mode = random.choice(modes)
        combo = {
            "test_id": i + 1,
            "origin": origin,
            "destination": dest,
            "max_connections": max_connections,
            "allowed_airlines": allowed_airlines,
            "mode": selected_mode # for random selection of mode
        }

        # 5. Execute test and catch failures for backtracking
        # 5. Execute test and catch failures for backtracking
        try:
            result = backend_search_api(
                origin=combo["origin"],
                destination=combo["destination"],
                max_connections=combo["max_connections"],
                allowed_airlines=combo["allowed_airlines"],
                mode=combo["mode"]  # <-- We added the mode here!
            )
            
            # You can add assertions here to test the result logic
            assert result["status"] == "success", "Backend returned a non-success status."
            
            print(f"✅ Test {combo['test_id']} Passed: {origin} -> {dest} (Mode: {selected_mode}, Max Conn: {max_connections})")
            
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