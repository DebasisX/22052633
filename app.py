from flask import Flask, jsonify
import requests
import time
from collections import deque
from datetime import datetime, timedelta

app = Flask(__name__)
app.debug = True

# config
WINDOW_SIZE = 10
BASE_API_URL = "http://20.244.56.144/evaluation-service/"
VALID_TYPES = {
    "p": "primes",
    "f": "fibo",
    "e": "even",
    "r": "rand"
}

# auth
AUTH_DETAILS = {
    "email": "debasis.sikder123@gmail.com",
    "name": "Debasis Sikdar",
    "rollNo": "22052633",
    "accessCode": "nwpwrZ",
    "clientID": "080feee3-80ea-4551-a860-00b8fd537813",
    "clientSecret": "MEAuYMxgdxMuzBqa"
}

# token
access_token = None
token_expiry = None

# data input
number_window = deque(maxlen=WINDOW_SIZE)

def get_auth_token():
    global access_token, token_expiry
    
    try:
        response = requests.post(
            f"{BASE_API_URL}auth",
            json=AUTH_DETAILS,
            timeout=2
        )
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data["access_token"]
        token_expiry = datetime.now() + timedelta(seconds=token_data["expires_in"] - 30)
        
        return True
    except Exception as e:
        print(f"Failed to get auth token: {str(e)}")
        return False

def refresh_token_if_needed():
    if not access_token or (token_expiry and datetime.now() >= token_expiry):
        return get_auth_token()
    return True

def fetch_numbers_from_api(number_type):
    if not refresh_token_if_needed():
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        start_time = time.time()
        response = requests.get(
            f"{BASE_API_URL}{number_type}",
            headers=headers,
            timeout=0.5
        )
        
        if (time.time() - start_time) > 0.5:
            return None
            
        if response.status_code == 200:
            data = response.json()
            if "numbers" in data:
                return data["numbers"]
            print("API response missing 'numbers' key")
        elif response.status_code == 401:
            print("Token expired, attempting refresh...")
            if get_auth_token():
                return fetch_numbers_from_api(number_type)
        
    except requests.Timeout:
        print("API request timed out (>500ms)")
    except requests.RequestException as e:
        print(f"API request failed: {str(e)}")
    
    return None

@app.route("/numbers/<string:type_key>", methods=["GET"])
def get_numbers(type_key):
    if type_key not in VALID_TYPES:
        return jsonify({
            "error": "Invalid number type. Use 'p' (primes), 'f' (Fibonacci), 'e' (even), or 'r' (random)."
        }), 400

    number_type = VALID_TYPES[type_key]
    previous_window = list(number_window)
    
    new_numbers = fetch_numbers_from_api(number_type)
    
    if new_numbers is None:
        return jsonify({
            "error": "Failed to fetch numbers from the API",
            "windowPrevState": previous_window,
            "windowCurrState": previous_window,
            "numbers": [],
            "avg": round(sum(number_window)/len(number_window), 2) if number_window else 0.0
        }), 200
    
    added_numbers = []
    for num in new_numbers:
        if num not in number_window:
            number_window.append(num)
            added_numbers.append(num)
    
    current_window = list(number_window)
    avg = round(sum(current_window)/len(current_window), 2) if current_window else 0.0
    
    return jsonify({
        "windowPrevState": previous_window,
        "windowCurrState": current_window,
        "numbers": new_numbers,
        "avg": avg
    })

@app.route("/")
def health_check():
    return jsonify({
        "status": "running",
        "window_size": WINDOW_SIZE,
        "valid_types": list(VALID_TYPES.keys())
    })

if __name__ == "__main__":
    if get_auth_token():
        app.run(host="0.0.0.0", port=9876)
    else:
        print("Failed to get initial authentication token. Server not started.")
