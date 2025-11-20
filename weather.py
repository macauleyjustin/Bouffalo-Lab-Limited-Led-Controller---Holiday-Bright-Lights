import socket
import time
import sys
import requests
import threading
from datetime import datetime

# --- CONFIGURATION ---
IP = "192.168.12.101"
PORT = 5577

# Free Weather API (Open-Meteo does not require an API key)
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# --- WREATH CONTROL (The "God Mode" Logic) ---
SEQ_NUM = 0x00

def get_transport_id():
    global SEQ_NUM
    tid = [0x00, 0x01, 0x02, SEQ_NUM]
    SEQ_NUM = (SEQ_NUM + 1) % 256
    return tid

def calculate_checksum(data):
    return (sum(data) + 198) % 256

def build_packet(inner_payload):
    transport = get_transport_id()
    length = len(inner_payload)
    len_hi = (length >> 8) & 0xFF
    len_lo = length & 0xFF
    data_block = transport + [len_hi, len_lo] + inner_payload
    outer_cs = calculate_checksum(data_block)
    header = [0xB0, 0xB1, 0xB2, 0xB3]
    return bytes(header + data_block + [outer_cs])

class WreathDriver:
    def __init__(self):
        self.sock = None
        self.connect()

    def connect(self):
        try:
            if self.sock: self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((IP, PORT))
            # Send wake up pulse
            self.send_raw([0x71, 0x23, 0x0F])
            return True
        except:
            return False

    def send_raw(self, payload):
        try:
            self.sock.send(build_packet(payload))
            time.sleep(0.05)
        except:
            self.connect()
            try: self.sock.send(build_packet(payload))
            except: pass

    def set_hsv(self, h, s, v):
        # E0 01 00 C1 [H] [S] [V] ...
        # Map Hue 0-360 -> 0-180
        h_byte = int(h / 2)
        payload = [0xE0, 0x01, 0x00, 0xC1, h_byte, s, v, 0,0,0,0,0x0A,0,0]
        
        # Send burst to ensure it sticks
        for _ in range(3):
            self.send_raw(payload)

# --- WEATHER LOGIC ---

def get_lat_lon(zip_code):
    try:
        params = {'name': zip_code, 'count': 1, 'language': 'en', 'format': 'json'}
        r = requests.get(GEO_URL, params=params)
        data = r.json()
        if 'results' in data:
            return data['results'][0]['latitude'], data['results'][0]['longitude'], data['results'][0]['name']
    except Exception as e:
        print(f"Error getting location: {e}")
    return None, None, None

def get_weather(lat, lon):
    try:
        params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'weather_code',
            'timezone': 'auto'
        }
        r = requests.get(WEATHER_URL, params=params)
        data = r.json()
        code = data['current']['weather_code']
        return code
    except Exception as e:
        print(f"Error getting weather: {e}")
        return None

def update_wreath(driver, code):
    # WMO Weather Codes
    # 0: Clear -> Yellow
    # 1-3: Cloudy -> Cyan/White dim
    # 51-67: Rain -> Blue
    # 71-77: Snow -> White
    # 80-82: Showers -> Purple
    # 95-99: Thunderstorm -> Purple/Red Flash? (Just Red for now)

    print(f"Weather Code: {code}")
    
    if code == 0:
        print("Forecast: CLEAR SKY -> Setting YELLOW")
        # Yellow: Hue 44
        driver.set_hsv(44, 100, 100)
        
    elif code in [1, 2, 3]:
        print("Forecast: CLOUDY -> Setting DIM WHITE")
        # White: Sat 0
        driver.set_hsv(0, 0, 50)
        
    elif code in [45, 48]:
        print("Forecast: FOG -> Setting DIM CYAN")
        driver.set_hsv(180, 50, 50)
        
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        print("Forecast: RAIN -> Setting BLUE")
        # Blue: Hue 240
        driver.set_hsv(240, 100, 100)
        
    elif code in [71, 73, 75, 77, 85, 86]:
        print("Forecast: SNOW -> Setting BRIGHT WHITE")
        # White: Sat 0, Val 100
        driver.set_hsv(0, 0, 100)
        
    elif code in [95, 96, 99]:
        print("Forecast: THUNDERSTORM -> Setting PURPLE")
        # Purple: Hue 300
        driver.set_hsv(300, 100, 100)
        
    else:
        print("Forecast: Unknown -> Setting GREEN (Default)")
        driver.set_hsv(120, 100, 100)

def main_loop():
    print("--- AUTOMATED WEATHER WREATH ---")
    zip_code = input("Enter your Zip Code (e.g., 48910): ")
    
    print("Locating...")
    lat, lon, name = get_lat_lon(zip_code)
    
    if not lat:
        print("Could not find location. Using Default (Lansing, MI).")
        lat, lon, name = 42.7325, -84.5555, "Lansing"
    
    print(f"Tracking Weather for: {name} ({lat}, {lon})")
    print(f"Connecting to Wreath at {IP}...")
    
    driver = WreathDriver()
    
    if not driver.connect():
        print("Error: Could not connect to Wreath. Check Wi-Fi.")
        # We continue anyway, it will try to reconnect in the loop
    
    print("\nStarting Auto-Update Loop (Every 60 Minutes)...")
    print("Press Ctrl+C to Stop.")
    
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{current_time}] Checking Forecast...")
            
            code = get_weather(lat, lon)
            
            if code is not None:
                update_wreath(driver, code)
            else:
                print("Failed to fetch weather data.")
            
            # Wait 1 hour (3600 seconds)
            # For testing, you can change this to 10 or 60
            time.sleep(3600) 
            
        except KeyboardInterrupt:
            print("\nStopping.")
            break
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(60) # Retry in a minute

if __name__ == "__main__":
    main_loop()
