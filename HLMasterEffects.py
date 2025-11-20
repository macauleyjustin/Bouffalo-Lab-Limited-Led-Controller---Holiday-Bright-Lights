import socket
import time
import colorsys
import random
import sys
import threading
import os
import math

# --- CONFIGURATION ---
DEFAULT_IP = "192.168.12.101"
PORT = 5577

# Prompt for IP and set global IP variable
print(f"Default IP is {DEFAULT_IP}")
user_ip = input("Enter Wreath IP Address (or press Enter to use default): ").strip()

if not user_ip:
    print(f"No IP provided. Using default: {DEFAULT_IP}")
    IP = DEFAULT_IP
else:
    # Basic validation 
    parts = user_ip.split('.')
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        print(f"Using Custom IP: {user_ip}")
        IP = user_ip
    else:
        print("Error: Invalid IP Address format.")
        sys.exit(1)

# --- COLOR & STATE CONSTANTS ---

# Verified HSV Colors (Hue/2, Sat, Val) - ADJUSTED for stability
COLOR_MAP = {
    "RED":    0x00, 
    "ORANGE": 0x0A, 
    "YELLOW": 0x16, 
    "GREEN":  0x3F,   # ADJUSTED: More stable Green endpoint
    "AQUA":   0x5A, 
    "BLUE":   0x80,   # ADJUSTED: More stable Blue endpoint
    "PURPLE": 0x96, 
    "PINK":   0xAA,
    "WHITE":  0,    "OFF":    0,
    "WARM":   20,   
    "COOL":   100   
}
# --- GLOBAL STATE ---
# Note: These are accessed by the animation thread and the main thread
SEQ_NUM = 0x00
RUNNING = True
CURRENT_MODE = "STATIC"
DRIVER = None

# --- PROTOCOL LAYER ---

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
        self.is_connected = self.connect()

    def connect(self):
        """Attempts connection and returns True/False."""
        try:
            if self.sock: self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2)
            self.sock.connect((IP, PORT))
            return True
        except:
            return False

    def send(self, payload):
        packet = build_packet(payload)
        try:
            # Send burst 3x for reliability
            for _ in range(3): 
                self.sock.send(packet)
                time.sleep(0.005) 
        except:
            # If failed, attempt reconnect and retry send once
            if self.connect():
                try: 
                    for _ in range(3):
                        self.sock.send(packet)
                        time.sleep(0.005)
                except: pass

    def set_hsv(self, h_byte, s_byte=100, v_byte=100):
        # Payload: E0 01 00 C1 [H] [S] [V] ...
        payload = [0xE0, 0x01, 0x00, 0xC1, h_byte, s_byte, v_byte, 0x00, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x00]
        self.send(payload)

    def turn_on(self):
        self.send([0x71, 0x23, 0x0F])

    def turn_off(self):
        self.send([0x71, 0x24, 0x0F])

# --- ANIMATION ENGINE ---
def get_hsv_byte(color_key):
    """Retrieves the [H, S, V] values for a color key."""
    # Lookup color map and return [H, S, V]
    hue_byte = COLOR_MAP.get(color_key, 0)
    
    if color_key == 'WHITE': return [0, 0, 100]
    if color_key == 'OFF': return [0, 0, 0]
    
    return [hue_byte, 100, 100]


def animation_loop():
    global RUNNING, CURRENT_MODE, DRIVER
    hue_deg = 0.0
    
    while RUNNING:
        try:
            if CURRENT_MODE == "RAINBOW":
                byte_val = int(hue_deg) % 180
                DRIVER.set_hsv(byte_val, 100, 100)
                hue_deg += 1
                time.sleep(0.05)

            elif CURRENT_MODE == "FIRE":
                # Original FIRE mode
                h = random.randint(0, 20)
                v = random.randint(50, 100)
                DRIVER.set_hsv(h, 100, v)
                time.sleep(random.uniform(0.05, 0.15))

            elif CURRENT_MODE == "THERMAL_FLAME":
                # Original Physics-Based Flame Simulation (Yellow/Orange focus)
                h_base = random.randint(0, 25) 
                v_flicker = int(15 * math.sin(time.time() * 20) + 85) 
                v_random = random.randint(80, 100)
                v_final = int((v_flicker + v_random) / 2)
                DRIVER.set_hsv(h_base, 100, v_final)
                time.sleep(random.uniform(0.02, 0.05))

            elif CURRENT_MODE == "THERMAL_FLAME_ADV":
                # --- ADVANCED PHYSICS CANDLE/FLAME SIMULATION ---
                
                # 1. HUE (Color Temperature)
                # Primary color is Red (0) to Orange/Yellow (20)
                h_flicker = random.randint(0, 20) 
                
                # 2. VALUE (Turbulence & Brightness)
                # High-frequency sine wave simulates air movement (80-100%)
                v_sin = int(10 * math.sin(time.time() * 15) + 90) 
                
                # Random external draft dimming (occasional 60-75% dip)
                v_draft = random.randint(70, 100) if random.random() < 0.95 else random.randint(50, 75)
                
                v_final = int((v_sin * 0.7 + v_draft * 0.3)) # Weighted average for chaos

                # 3. WICK EFFECT (Blue Base Simulation - Hottest Zone)
                # Occasionally pulse a slight Aqua tint to simulate the hottest core.
                if random.random() < 0.02:
                    # Brief, hottest pulse (High Blue Hue, low saturation)
                    DRIVER.set_hsv(COLOR_MAP["AQUA"], 50, 90) 
                    time.sleep(0.02)
                
                # Set the main warm color
                DRIVER.set_hsv(h_flicker, 100, v_final)
                time.sleep(random.uniform(0.01, 0.04)) # Fast update rate for fluid motion

            elif CURRENT_MODE == "POLICE":
                # Red / Blue Strobe
                for _ in range(3):
                    DRIVER.set_hsv(COLOR_MAP["RED"], 100, 100); time.sleep(0.08)
                    DRIVER.set_hsv(COLOR_MAP["RED"], 100, 0); time.sleep(0.08)
                for _ in range(3):
                    DRIVER.set_hsv(COLOR_MAP["BLUE"], 100, 100); time.sleep(0.08)
                    DRIVER.set_hsv(COLOR_MAP["BLUE"], 100, 0); time.sleep(0.08)

            elif CURRENT_MODE == "WAVES":
                # Breathing effect (slow cycle of brightness)
                brightness = int(50 * math.sin(time.time() * 0.5) + 50)
                DRIVER.set_hsv(COLOR_MAP["AQUA"], 100, brightness)
                time.sleep(0.05)
            
            elif CURRENT_MODE == "TWINKLE":
                # Twinkle/Sparkle effect (random color on 5% of cycles)
                base_h, base_s, base_v = get_hsv_byte("PURPLE")
                if random.random() < 0.05:
                    DRIVER.set_hsv(COLOR_MAP["YELLOW"], 50, 100) 
                    time.sleep(0.05)
                else:
                    DRIVER.set_hsv(base_h, base_s, 70)
                    time.sleep(0.1)

            elif CURRENT_MODE == "SPARKLING":
                # Quick flicker between two specific colors (like Pink and Aqua)
                if int(time.time() * 10) % 2 == 0:
                    DRIVER.set_hsv(COLOR_MAP["PINK"], 100, 100)
                else:
                    DRIVER.set_hsv(COLOR_MAP["AQUA"], 100, 100)
                time.sleep(0.1)
            
            elif CURRENT_MODE == "THUNDERSTORM":
                # Solid Ambient Background (Deep Blue - 50% brightness)
                DRIVER.set_hsv(COLOR_MAP["BLUE"], 100, 50) 
                
                if random.random() < 0.005: 
                    strike_gap = random.uniform(5, 15) 
                    
                    # Primary Strike 
                    DRIVER.set_hsv(COLOR_MAP["WHITE"], 0, 100)
                    time.sleep(0.05) 
                    
                    # Secondary Flicker/Restrikes 
                    num_flickers = random.randint(0, 3)
                    for _ in range(num_flickers):
                        DRIVER.set_hsv(COLOR_MAP["WHITE"], 0, random.randint(40, 80))
                        time.sleep(random.uniform(0.04, 0.08))
                        
                        DRIVER.set_hsv(COLOR_MAP["BLUE"], 100, 40) 
                        time.sleep(0.03)
                    
                    time.sleep(strike_gap)
                
                time.sleep(0.2)
            
            elif CURRENT_MODE == "WHITE_SPARKLE":
                if int(time.time() * 5) % 2 == 0:
                    DRIVER.set_hsv(COLOR_MAP["COOL"], 0, 100)
                else:
                    DRIVER.set_hsv(COLOR_MAP["WARM"], 0, 100)
                time.sleep(0.2)

            elif CURRENT_MODE == "HOLLY":
                if int(time.time() * 2) % 2 == 0:
                    h = COLOR_MAP["RED"]
                else:
                    h = COLOR_MAP["GREEN"]
                
                brightness = int(20 * math.sin(time.time() * 4) + 80)
                DRIVER.set_hsv(h, 100, brightness)
                time.sleep(0.1)

            elif CURRENT_MODE == "CANDYCANE":
                if int(time.time() * 4) % 2 == 0:
                    DRIVER.set_hsv(COLOR_MAP["RED"], 100, 100)
                else:
                    DRIVER.set_hsv(COLOR_MAP["WHITE"], 0, 100)
                time.sleep(0.15)
            
            elif CURRENT_MODE == "FROSTY":
                brightness = int(50 * math.sin(time.time() * 0.4) + 50) 
                DRIVER.set_hsv(COLOR_MAP["BLUE"], 50, brightness)
                time.sleep(0.1)

            elif CURRENT_MODE == "SIREN":
                t = int(time.time() * 20) % 3
                if t == 0:
                    DRIVER.set_hsv(COLOR_MAP["RED"], 100, 100)
                elif t == 1:
                    DRIVER.set_hsv(COLOR_MAP["WHITE"], 0, 100)
                else:
                    DRIVER.set_hsv(COLOR_MAP["BLUE"], 100, 100)
                time.sleep(0.05)

            elif CURRENT_MODE == "GRAVITY":
                t = time.time() * 3 
                brightness = int(100 * (abs(math.sin(t)**5))) 
                DRIVER.set_hsv(COLOR_MAP["ORANGE"], 100, brightness)
                time.sleep(0.03)

            elif CURRENT_MODE == "COMET":
                brightness = int(50 * math.sin(time.time() * 2) + 50)
                h_cycle = int(math.sin(time.time() * 0.5) * 60 + 130)
                DRIVER.set_hsv(h_cycle, 100, brightness)
                time.sleep(0.04)

            elif CURRENT_MODE == "PLASMA":
                h_shift = int(50 * math.sin(time.time() * 0.1) + 120) 
                s_shift = int(15 * math.cos(time.time() * 0.3) + 85)
                v_shift = int(10 * math.sin(time.time() * 0.2) + 60)
                
                DRIVER.set_hsv(h_shift, s_shift, v_shift)
                time.sleep(0.1)
            
            else:
                # STATIC mode sleep to prevent 100% CPU usage
                time.sleep(0.5)
        
        except Exception:
            time.sleep(1)

# --- UI and Main ---

def main():
    global DRIVER, CURRENT_MODE
    DRIVER = WreathDriver()
    
    if not DRIVER.is_connected:
        print(f"\nFatal Error: Could not connect to Wreath at {IP}. Please verify IP or Wi-Fi.")
        return

    DRIVER.turn_on()
    
    # Start Animation Thread
    t = threading.Thread(target=animation_loop)
    t.daemon = True
    t.start()

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"--- WREATH ANIMATION MASTER ({IP}) ---")
        print(f"STATUS: {CURRENT_MODE}")
        print("---------------------------------------")
        
        # CHRISTMAS MODES
        print(" [1] Rainbow Swirl")
        print(" [2] Christmas Fire (Original)")
        print(" [C] Candy Cane (Red/White)")
        print(" [H] Holly (Red/Green Pulse)")
        print(" [F] Frosty Fade (Icy Blue)")
        
        # PHYSICS & COMPLEX MODES
        print(" [T] Thermal Flame (Physics Fire)") # The new, realistic flame
        print(" [A] Advanced Thermal Flame (Candle Physics)") # The new, refined flame
        print(" [G] Gravity Bounce (Physics Sim)")
        print(" [M] Comet Wash (Circular Chase)")
        print(" [P] Plasma Nebula (Slow Chaos)")
        
        # SPECIAL DYNAMIC MODES
        print(" [W] Waves (Breathing Aqua)")
        print(" [I] Twinkle (Icy Purple/Yellow)")
        print(" [S] Sparkling (Pink/Aqua Flicker)")
        print(" [5] White Sparkle (Warm/Cool)")
        
        # HAZARD & WEATHER
        print(" [4] THUNDERSTORM (Realistic)")
        print(" [L] Police Siren (Red/White/Blue)")
        
        print("---------------------------------------")
        print(" [R] Red   [G] Green  [B] Blue")
        print(" [0] OFF / Stop Loop")
        print(" [Q] Quit Program")
        
        cmd = input("Select Mode > ").upper()
        
        if cmd == 'Q':
            global RUNNING
            RUNNING = False
            DRIVER.turn_off()
            break
        
        # --- DYNAMIC MODES ---
        elif cmd == 'W': CURRENT_MODE = "WAVES"
        elif cmd == 'S': CURRENT_MODE = "SPARKLING"
        elif cmd == 'I': CURRENT_MODE = "TWINKLE"
        elif cmd == '1': CURRENT_MODE = "RAINBOW"
        elif cmd == '2': CURRENT_MODE = "FIRE"
        elif cmd == '3': CURRENT_MODE = "POLICE"
        elif cmd == '4': CURRENT_MODE = "THUNDERSTORM" 
        elif cmd == '5': CURRENT_MODE = "WHITE_SPARKLE" 
        
        # --- CHRISTMAS MODES ---
        elif cmd == 'C': CURRENT_MODE = "CANDYCANE"
        elif cmd == 'H': CURRENT_MODE = "HOLLY"
        elif cmd == 'F': CURRENT_MODE = "FROSTY"
        elif cmd == 'L': CURRENT_MODE = "SIREN"
        
        # --- PHYSICS/COMPLEX MODES ---
        elif cmd == 'G': CURRENT_MODE = "GRAVITY"
        elif cmd == 'M': CURRENT_MODE = "COMET"
        elif cmd == 'P': CURRENT_MODE = "PLASMA"
        elif cmd == 'T': CURRENT_MODE = "THERMAL_FLAME" 
        elif cmd == 'A': CURRENT_MODE = "THERMAL_FLAME_ADV" # New Advanced Flame

        # --- STATIC COLORS ---
        elif cmd in ['R','G','B']:
            CURRENT_MODE = "STATIC"
            h_byte = COLOR_MAP.get(cmd, 0)
            DRIVER.set_hsv(h_byte, 100, 100)
        
        # --- OFF ---
        elif cmd == '0': 
            CURRENT_MODE = "STATIC"
            DRIVER.turn_off()
            
if __name__ == "__main__":
    main()
