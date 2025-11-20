Holiday Bright Lights "Brilliant" Wreath - Reverse Engineering Documentation

1. Overview

This project successfully reverse-engineered the proprietary control protocol for the "Holiday Bright Lights" Brilliant Series Wreath (Model AK001-ZJ21413). This device masquerades as a standard "Magic Home" controller but uses a locked, encrypted tunnel protocol ("Surplife Pro") that rejects standard commands.

Hardware Profile:

Chipset: Bouffalo Lab (RISC-V), likely BL602 series.

Module: High-Flying (HF-LPT100 series).

Discovery Name: HF-A11ASSISTHREAD

Port: TCP 5577 (Control) & UDP 48899 (Discovery).

2. The Protocol Discovery

Initial attempts using standard libraries (flux_led, tinytuya) failed because the device implements a non-standard "Tunnel" protocol.

The Discovery Process

Port Scan: Confirmed TCP 5577 was open.

Traffic Analysis: PCAPdroid captures revealed the app communicating with 192.168.12.101.

Packet Inspection: The app was sending packets starting with B0 B1 B2 B3, not the standard 31 or 81.

The "Tunnel" Hypothesis: We theorized the device ignores raw commands unless wrapped in this header.

3. The "Tunnel" Protocol Specification

All commands must be wrapped in a 16-byte transport header.

Structure:
[Header] [Transport ID] [Length] [Payload] [Checksum]

Header (4 Bytes): B0 B1 B2 B3 (Fixed Preamble)

Transport ID (4 Bytes): 00 01 02 XX (Where XX is a rolling sequence number).

Length (2 Bytes): Big Endian length of the Payload + Inner Checksum.

Payload (Variable): The actual command (e.g., E0 01...).

Outer Checksum (1 Byte): Calculated as (Sum(Data) + 198) % 256.

The "Magic Math":
The checksum logic was the hardest nut to crack. Standard Magic Home uses Sum % 256.
By analyzing packet dumps (Sum=730, Checksum=A0), we solved for the offset:
Checksum = (Sum of Bytes - 58) % 256 (or +198).

4. The Command Set

Once inside the tunnel, the device speaks a "Native HSV" language, not RGB.

Set Color (0xE0)

This command sets the global color for the entire wreath.
Format: E0 01 00 C1 [Hue] [Sat] [Val] 00 00 00 00 0A 00 00

Hue: 0-180 (Maps to 0-360 degrees).

00 = Red

16 = Yellow (44 deg)

3C = Green (120 deg)

5A = Aqua (180 deg)

78 = Blue (240 deg)

96 = Purple (300 deg)

Sat: 0-100 (Saturation). 0 = White.

Val: 0-100 (Brightness). 0 = Off.

Pixel Control (0xE1 0x26)

Allows individual pixel addressing via bitmasking.
Format: E1 26 [IdxHi] [IdxLo] [Hue] [Sat] [Val] [Mask...]

5. The Solution

We developed a Python driver (wreath_weather.py) that:

Manages Connection: Auto-reconnects on timeout (Bouffalo chips sleep aggressively).

Encapsulates Data: Wraps standard commands in the B0 B1 tunnel.

Applies Checksum: Calculates the proprietary +198 checksum.

Integrates Logic: Connects to Open-Meteo API to change wreath color based on local weather conditions.

6. How to Use

Install Requirements: pip install requests

Run: python3 wreath_weather.py

Enjoy: The wreath is now a smart weather station.

Reverse Engineered by User & Gemini, November 2025.
