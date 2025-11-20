import socket
import time
import sys
import os

# --- CONFIGURATION ---
IP = "192.168.12.101"
PORT = 5577

# Morse Code Dictionary
MORSE_CODE_DICT = { 'A':'.-', 'B':'-...',
                    'C':'-.-.', 'D':'-..', 'E':'.',
                    'F':'..-.', 'G':'--.', 'H':'....',
                    'I':'..', 'J':'.---', 'K':'-.-',
                    'L':'.-..', 'M':'--', 'N':'-.',
                    'O':'---', 'P':'.--.', 'Q':'--.-',
                    'R':'.-.', 'S':'...', 'T':'-',
                    'U':'..-', 'V':'...-', 'W':'.--',
                    'X':'-..-', 'Y':'-.--', 'Z':'--..',
                    '1':'.----', '2':'..---', '3':'...--',
                    '4':'....-', '5':'.....', '6':'-....',
                    '7':'--...', '8':'---..', '9':'----.',
                    '0':'-----', ', ':'--..--', '.':'.-.-.-',
                    '?':'..--..', '/':'-..-.', '-':'-....-',
                    '(':'-.--.', ')':'-.--.-', ' ': ' '}

# Colors (Hue/2, Sat, Val)
COLORS = {
    "RED":    [0, 100, 100],
    "GREEN":  [60, 100, 100],
    "BLUE":   [120, 100, 100],
    "YELLOW": [22, 100, 100],
    "PURPLE": [150, 100, 100],
    "CYAN":   [90, 100, 100],
    "WHITE":  [0, 0, 100],
    "OFF":    [0, 0, 0]
}

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

class WreathComm:
    def __init__(self):
        self.sock = None

    def connect(self):
        try:
            if self.sock: self.sock.close()
        except: pass
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2)
            self.sock.connect((IP, PORT))
            return True
        except:
            return False

    def send_burst(self, payload):
        packet = build_packet(payload)
        try:
            for _ in range(3):
                self.sock.send(packet)
                time.sleep(0.005) # Very fast burst
        except:
            if self.connect():
                try:
                    for _ in range(3):
                        self.sock.send(packet)
                        time.sleep(0.005)
                except: pass

    def set_color(self, color_name):
        vals = COLORS.get(color_name, [0,0,0])
        payload = [0xE0, 0x01, 0x00, 0xC1, vals[0], vals[1], vals[2], 0,0,0,0,0x0A,0,0]
        self.send_burst(payload)

    def flash_morse(self, text, on_color, off_color, wpm):
        # Calculate timing based on Standard PARIS method
        # T_dot = 1200 / WPM (ms) -> 1.2 / WPM (sec)
        if wpm < 1: wpm = 1
        if wpm > 50: wpm = 50
        
        t_unit = 1.2 / wpm
        
        print(f"TRANSMITTING: '{text}' @ {wpm} WPM (Dot: {t_unit:.2f}s)")
        self.connect()
        
        try:
            while True: # Loop forever
                for char in text.upper():
                    if char == ' ':
                        time.sleep(t_unit * 7) # Word Gap (7 units)
                        continue
                    
                    if char not in MORSE_CODE_DICT: continue
                    
                    code = MORSE_CODE_DICT[char]
                    sys.stdout.write(f"{char}:{code} ")
                    sys.stdout.flush()
                    
                    for symbol in code:
                        self.set_color(on_color)
                        
                        if symbol == '.':
                            time.sleep(t_unit * 1) # Dot (1 unit)
                        elif symbol == '-':
                            time.sleep(t_unit * 3) # Dash (3 units)
                        
                        self.set_color(off_color)
                        time.sleep(t_unit * 1) # Inter-symbol gap (1 unit)
                    
                    time.sleep(t_unit * 3) # Letter gap (3 units)
                
                print("\n[Repeating... Ctrl+C to Stop]")
                time.sleep(t_unit * 7) # Message gap
                
        except KeyboardInterrupt:
            print("\nSTOPPED.")
            self.set_color("OFF")

    def flash_binary(self, text, one_color, zero_color, bps):
        if bps < 0.1: bps = 0.1
        
        # Time per bit
        t_total = 1.0 / bps
        # We use 80% ON time, 20% Gap time to make bits distinct
        t_on = t_total * 0.8
        t_gap = t_total * 0.2
        
        print(f"TRANSMITTING BINARY: '{text}' @ {bps} BPS")
        self.connect()
        
        binary_str = ''.join(format(ord(c), '08b') for c in text)
        print(f"Stream Length: {len(binary_str)} bits")
        
        try:
            while True: # Loop forever
                for bit in binary_str:
                    if bit == '1':
                        self.set_color(one_color)
                        sys.stdout.write("1")
                    else:
                        self.set_color(zero_color)
                        sys.stdout.write("0")
                    sys.stdout.flush()
                    
                    time.sleep(t_on)
                    
                    # Brief Gap to separate bits visually
                    self.set_color("OFF")
                    time.sleep(t_gap)
                    
                print("\n[Repeating... Ctrl+C to Stop]")
                time.sleep(1.0)

        except KeyboardInterrupt:
            print("\nSTOPPED.")
            self.set_color("OFF")

if __name__ == "__main__":
    comm = WreathComm()
    
    # Initial Wakeup
    if comm.connect():
        print(f"Connected to {IP}")
        comm.set_color("OFF")
    
    while True:
        print("\n--- WREATH TELEGRAPH ---")
        print("[1] Morse Code (Variable WPM)")
        print("[2] Binary Stream (Variable BPS)")
        print("[Q] Quit")
        
        mode = input("Select > ").upper()
        
        if mode == 'Q': break
        
        if mode == '1':
            txt = input("Message: ")
            col = input("Color [GREEN]: ").upper() or "GREEN"
            try:
                wpm = float(input("Speed (1-50 WPM) [15]: ") or 15)
            except:
                wpm = 15
            comm.flash_morse(txt, col, "OFF", wpm)
            
        elif mode == '2':
            txt = input("Message: ")
            c1 = input("Color for '1' [BLUE]: ").upper() or "BLUE"
            c0 = input("Color for '0' [RED]: ").upper() or "RED"
            try:
                bps = float(input("Speed (Bits Per Sec) [2]: ") or 2)
            except:
                bps = 2
            comm.flash_binary(txt, c1, c0, bps)
