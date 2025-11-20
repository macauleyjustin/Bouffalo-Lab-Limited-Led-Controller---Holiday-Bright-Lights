import socket
import time
import colorsys
import random
import sys
import threading
import os

# --- CONFIGURATION ---
IP = "192.168.12.101"
PORT = 5577

# --- PROTOCOL CONSTANTS ---
# The device divides the 360-degree color wheel by 2
# Hue 0-180 maps to 0-360 degrees
COLOR_MAP = {
    "RED":    0x00, # 0 deg
    "ORANGE": 0x0A, # 20 deg
    "YELLOW": 0x16, # 44 deg
    "GREEN":  0x3C, # 120 deg
    "AQUA":   0x5A, # 180 deg
    "BLUE":   0x78, # 240 deg
    "PURPLE": 0x96, # 300 deg
    "PINK":   0xAA, # 340 deg
}

# Global State
SEQ_NUM = 0x00
RUNNING = True
CURRENT_MODE = "STATIC"
DRIVER = None

# --- NETWORK LAYER ---
def get_transport_id():
    global SEQ_NUM
    tid = [0x00, 0x01, 0x02, SEQ_NUM]
    SEQ_NUM = (SEQ_NUM + 1) % 256
    return tid

def calculate_checksum(data):
    # Verified Algorithm: Sum - 58 (or +198)
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
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((IP, PORT))
        except:
            pass

    def send(self, payload):
        try:
            self.sock.send(build_packet(payload))
            time.sleep(0.02)
        except:
            self.connect()
            try: self.sock.send(build_packet(payload))
            except: pass

    def set_hsv(self, h_byte, s_byte=100, v_byte=100):
        # Payload: E0 01 00 C1 [Hue] [Sat] [Val] 00 ...
        # Uses the captured values (0x64 = 100%) directly
        payload = [0xE0, 0x01, 0x00, 0xC1, h_byte, s_byte, v_byte, 0x00, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x00]
        self.send(payload)

    def set_white(self, warm=0, cool=0):
        # Based on your Slot tests: Slot 3=CW, Slot 5=WW
        # The protocol likely maps specific bytes to W/C
        # Let's use the raw E0 structure but zero out RGB
        # E0 01 00 C1 00 00 00 [CW] 00 [WW] ... (Hypothetical mapping from Slots)
        # Actually, HSV mode usually turns off White automatically.
        # If you need White, we send Saturation 0.
        if warm > 0 or cool > 0:
            # Low Saturation = White
            # Hue determines temp? (0=Warm, 100=Cool?)
            # Let's just use the captured "Sat=0" trick for now
            self.set_hsv(0, 0, 100)
        else:
            self.turn_off()

    def turn_on(self):
        self.send([0x71, 0x23, 0x0F])

    def turn_off(self):
        self.send([0x71, 0x24, 0x0F])

# --- ANIMATION ENGINE ---
def animation_loop():
    global RUNNING, CURRENT_MODE, DRIVER
    hue_deg = 0.0
    
    while RUNNING:
        if CURRENT_MODE == "RAINBOW":
            # Cycle 0-180 Byte
            byte_val = int(hue_deg) % 180
            DRIVER.set_hsv(byte_val, 100, 100)
            hue_deg += 1
            time.sleep(0.05)

        elif CURRENT_MODE == "FIRE":
            # Red (00) to Yellow (16)
            h = random.randint(0, 20)
            v = random.randint(50, 100)
            DRIVER.set_hsv(h, 100, v)
            time.sleep(random.uniform(0.05, 0.15))

        elif CURRENT_MODE == "POLICE":
            for _ in range(3):
                DRIVER.set_hsv(COLOR_MAP["RED"], 100, 100); time.sleep(0.08)
                DRIVER.set_hsv(COLOR_MAP["RED"], 100, 0); time.sleep(0.08)
            for _ in range(3):
                DRIVER.set_hsv(COLOR_MAP["BLUE"], 100, 100); time.sleep(0.08)
                DRIVER.set_hsv(COLOR_MAP["BLUE"], 100, 0); time.sleep(0.08)
        
        else:
            time.sleep(0.5)

# --- UI ---
def main():
    global CURRENT_MODE, RUNNING, DRIVER
    DRIVER = WreathDriver()
    DRIVER.turn_on()
    
    t = threading.Thread(target=animation_loop)
    t.daemon = True
    t.start()

    while True:
        if os.name == 'nt': os.system('cls')
        else: os.system('clear')
        
        print(f"--- HOLIDAY BRIGHT WREATH ({IP}) ---")
        print(f"STATUS: {CURRENT_MODE}")
        print("-------------------------------")
        print(" [1] Rainbow Swirl")
        print(" [2] Christmas Fire")
        print(" [3] Police Strobe")
        print(" [R] Red")
        print(" [G] Green")
        print(" [B] Blue")
        print(" [A] Aqua")
        print(" [P] Purple")
        print(" [Y] Yellow")
        print(" [W] White")
        print(" [0] OFF")
        print(" [Q] Quit")
        
        cmd = input("\nCommand > ").upper()
        
        if cmd == 'Q':
            RUNNING = False
            break
        elif cmd == '1': CURRENT_MODE = "RAINBOW"
        elif cmd == '2': CURRENT_MODE = "FIRE"
        elif cmd == '3': CURRENT_MODE = "POLICE"
        elif cmd == '0': 
            CURRENT_MODE = "STATIC"
            DRIVER.turn_off()
        
        elif cmd in ['R','G','B','A','P','Y','W']:
            CURRENT_MODE = "STATIC"
            if cmd == 'R': DRIVER.set_hsv(COLOR_MAP["RED"])
            elif cmd == 'G': DRIVER.set_hsv(COLOR_MAP["GREEN"])
            elif cmd == 'B': DRIVER.set_hsv(COLOR_MAP["BLUE"])
            elif cmd == 'A': DRIVER.set_hsv(COLOR_MAP["AQUA"])
            elif cmd == 'P': DRIVER.set_hsv(COLOR_MAP["PURPLE"])
            elif cmd == 'Y': DRIVER.set_hsv(COLOR_MAP["YELLOW"])
            elif cmd == 'W': DRIVER.set_hsv(0, 0, 100)

if __name__ == "__main__":
    main()
