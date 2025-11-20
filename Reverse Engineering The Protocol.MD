The Wreath Liberation Project: Reverse Engineering the "Brilliant" Protocol

Project Goal

To bypass the manufacturer's restrictive cloud/BLE application and achieve local, scriptable control over the Holiday Bright Lights "Brilliant" wreath, allowing for custom physics-based effects, telegraphy, and automation.
1. Initial Diagnosis and Fingerprinting
The first step was identifying the underlying hardware, as the "Brilliant" app is a white-label facade.

1.1 Hardware Identification

MAC Address: Initial Bluetooth scans revealed the MAC prefix B4:E8:42. A public OUI lookup confirmed this vendor as Bouffalo Lab Limited, manufacturers of low-cost Wi-Fi/BLE integrated circuits (SoCs, like the BL602/BL604 series).

Device Name: The controller advertised itself as IOTWFC00 and the network scan revealed the hostname ZENGGE-a7fc00.lan. This identified the firmware as a variant of the widely cloned Zengge / Magic Home / Surplife ecosystem.

1.2 Connectivity Model

Initial attempts at BLE control failed. This, combined with the device's name (IOTWFC00), confirmed a BLE-to-Wi-Fi Handoff Model:
BLE (Bluetooth Low Energy): Used strictly for initial pairing and transmitting Wi-Fi credentials.
Wi-Fi (TCP): Used for all real-time control commands once the device is connected to the router (192.168.12.101).

2. Phase I: Breaking the Communication Wall
Standard libraries failed to connect to the device's control port (TCP 5577) because the device was not speaking standard "Magic Home" language.

2.1 The TCP Barrier
Port Confirmation: An Nmap scan confirmed TCP Port 5577 was open, confirming the Magic Home architecture.
Failure Mode: Simple raw commands (0x31 for color) and library attempts consistently failed. Crucially, the legacy "Power On/Off" command (0x71 0x23 0x0F) worked, proving the network link was sound, but the command syntax for color was incorrect.

2.2 The Tunnel and Checksum Discovery (The Encryption Key)
The key to unlocking the protocol was analyzing the raw TCP packets captured via PCAPdroid while the official app was running.
Tunnel Header: We identified that every packet was encapsulated (wrapped) in a specific 4-byte header: B0 B1 B2 B3. This indicated a proprietary transport layer was required for non-legacy commands.
Checksum Discrepancy: The app's packets were not using the standard Sum % 256 checksum. By comparing the sum of the packet data to the final checksum byte (0xA0 or 0x0B) across multiple captures, we solved the formula:
$$\text{Checksum} = (\text{Sum of all Payload Bytes} + 198) \pmod{256}$$
(This is mathematically equivalent to $\text{Sum} - 58$). This offset was the unique "password" that validated all commands.
Command Validation: The "OFF" command (0x71 0x24 0x0F) worked in the final script because it successfully passed this custom checksum calculation.

3. Phase II: Cracking the Color Language (HSV)
With the secure tunnel established, we had to determine the language spoken inside the tunnel.

3.1 Command Format Discovery
Packet captures revealed the full command structure:
$$\text{COMMAND} = \text{E0 01 00 C1} \; [HUE] \; [SAT] \; [VAL] \; \text{[Padding]}$$
The first four bytes (E0 01 00 C1) serve as the Set Color Header for this specific Bouffalo firmware.

3.2 HSV Mapping (The Final Breakthrough)
By capturing the exact hex values sent when setting primary colors (Red, Green, Blue, Purple) in the app, we discovered the device uses a non-standard HSV (Hue, Saturation, Value) model:
Color Set in App
Captured Hue Byte
Decimal
Conclusion
Red
00
0
HUE Byte 0 is Red.
Green
3C
60
HUE Angle is mapped 2:1 (60 * 2 = 120° Green).
Blue
78
120
HUE Angle is mapped 2:1 (120 * 2 = 240° Blue).
Purple
96
150
HUE Angle is mapped 2:1 (150 * 2 = 300° Purple).
This confirmed the Hue Byte = Hue Angle / 2 relationship, which is vital for smooth color cycling.

4. Final Implementation

The final Python application (controllights.py) now runs a driver that handles the continuous handshake, calculation, and transmission of the correct packets, enabling reliable operation of all complex modes:
Reliability: Uses the calculated tunnel and burst-send methodology to beat the device's aggressive sleep timer.
Physics Modes: Utilizes the discovered HSV protocol to run advanced algorithms that simulate real-world phenomena (e.g., THERMAL_FLAME uses sine waves and random noise on the Hue and Value channels for realistic flicker).

Portability: The IP address is configurable on startup to handle DHCP changes.