```markdown
# Holiday Bright Lights "Brilliant" Wreath – Reverse Engineering Documentation

Successfully reverse-engineered the proprietary control protocol for the **Holiday Bright Lights Brilliant Series Wreath** (Model: AK001-ZJ21413).

This device pretends to be a generic "Magic Home" / "Flux LED" Wi-Fi controller but actually runs a locked, encrypted "tunnel" protocol branded as **Surplife Pro** inside the official app. Standard open-source libraries (flux_led, tinytuya, etc.) are deliberately rejected.

**Reverse Engineered by a determined human + Grok/Gemini – November 2025**

## 1. Hardware Profile

| Attribute          | Value                                      |
|---------------------|--------------------------------------------|
| SoC                 | Bouffalo Lab RISC-V (most likely BL602/BL604) |
| Wi-Fi Module        | High-Flying HF-LPT100 series (or similar) |
| Discovery Name      | `HF-A11ASSISTHREAD`                       |
| Discovery Protocol  | UDP 48899                                  |
| Control Port        | TCP 5577                                   |

## 2. Protocol Discovery Process

Standard tools failed → time to go full packet-sniper mode:

- Port scan confirmed only TCP 5577 open
- PCAPdroid / Wireshark captures of the official "Surplife Pro" app
- Every packet from the app starts with the magic bytes `B0 B1 B2 B3 …`
- Hypothesis: the chip completely ignores raw LED commands unless they are wrapped in this proprietary 16-byte "tunnel" header

## 3. The "Tunnel" Protocol (Surplife Pro Encryption Layer)

All real commands must be encapsulated in the following wrapper:

| Bytes | Field              | Value / Description                                      |
|-------|--------------------|----------------------------------------------------------|
| 0-3   | Preamble           | Fixed: `B0 B1 B2 B3`                                     |
| 4-7   | Transport ID       | `00 01 02 XX` – XX is an incrementing sequence number   |
| 8-9   | Payload Length     | Big-endian length of (Payload + 1-byte inner checksum)   |
| 10-n  | Payload            | Actual inner command (e.g., `E0 01 …`)                   |
| n+1   | Outer Checksum     | `(sum(all bytes from preamble to end of payload) + 198) & 0xFF` |

### The Magic Checksum Math

Standard MagicHome: `checksum = sum(bytes) % 256`  
This device: `checksum = (sum(bytes) + 198) % 256` → equivalent to `-58 mod 256`

Discovered by taking a real packet where sum-of-bytes = 730 → transmitted checksum byte = 0xA0  
→ 730 + X ≡ 160 mod 256 → X = 198 (or equivalently subtract 58).

## 4. Inner Command Set (once inside the tunnel)

After decryption, the device speaks a **native HSV** protocol, not RGB.

### 4.1 Set Global Color (0xE0)

```
E0 01 00 C1 [H] [S] [V] 00 00 00 00 0A 00 00
```

| Byte | Meaning              | Range    | Notes                                      |
|------|----------------------|----------|--------------------------------------------|
| H    | Hue                  | 0–180    | Maps to 0–360° (multiply by 2)             |
|      | 0x00                 | Red      |                                            |
|      | 0x3C                 | Green    |                                            |
|      | 0x78                 | Blue     |                                            |
| S    | Saturation           | 0–100    | 0 = white                                  |
| V    | Value / Brightness   | 0–100    | 0 = off                                    |

### 4.2 Individual Pixel Control (0xE1 0x26)

Allows bitmasked addressing of specific LEDs (wreath has ~80–100 pixels depending on size).

Format is more complex and only partially reverse-engineered so far – global color (0xE0) is sufficient for most effects.

## 5. Practical Result – Python Driver

A fully working driver is available here: [`wreath_weather.py`](wreath_weather.py)

Features:
- Automatic reconnection (Bouffalo chips aggressively sleep)
- Correct tunnel encapsulation + +198 checksum
- HSV → wreath color conversion
- Integration with Open-Meteo API → wreath displays current weather:
  - Blue/cyan = cold
  - Red/orange = hot
  - Purple = precipitation
  - White flashing = snow / storms

### Usage

```bash
pip install requests
python3 wreath_weather.py <wreath_ip> [latitude] [longitude]
```

Your Christmas wreath is now officially the world’s most over-engineered weather station.

## Acknowledgments

- The anonymous reverse-engineer who spent three evenings staring at hex dumps
- Grok & Gemini for helping solve the checksum offset in < 5 minutes
- Bouffalo Lab for making a perfectly good open-source RISC-V chip… then locking everything down for Christmas lights

Merry hacking and happy holidays! 🎄
```

Copy-paste this into a `README.md` on GitHub and it will render beautifully. Add the Python script in the same repo and you're good to go. 🚀
