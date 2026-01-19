# RS485 to Ethernet Module Installation Guide

## Overview

This guide provides step-by-step instructions for installing a 2-Channel RS485 to Ethernet adapter module to connect Modbus devices (thermostats) to a network.

## Hardware Requirements

- 2-CH RS485 to Ethernet adapter module
- Existing 24V DC transformer
- RS485/Modbus devices (e.g., thermostats)
- Appropriate wiring (shielded twisted pair recommended for RS485)

## Module Specifications

- **Power Input**: 6-36V DC (24V DC typical)
- **RS485 Channels**: 2 independent channels
- **Ethernet Ports**: 2 ports (either can be used for network, other for cascading)

## Connection Diagram

### Power Connections

```
24V DC Transformer          RS485 Module
┌─────────────┐            ┌──────────────────┐
│             │            │                  │
│    + 24V ───┼────────────┼──→ 6-36V Input   │
│             │            │                  │
│    - GND ───┼────────────┼──→ Ground        │
│             │            │                  │
└─────────────┘            └──────────────────┘
```

### RS485 Data Connections

```
Electrical Panel                    RS485 Module
XCOM Terminal Group                 
┌──────────────────────┐           ┌─────────────────────┐
│                      │           │                     │
│  Device 1 (String 1) │           │   RS485 Channel 1   │
│  ├─ T+ (Data+) ──────┼───────────┼──→ A                │
│  ├─ T- (Data-) ──────┼───────────┼──→ B                │
│  └─ GND ─────────────┼───────────┼──→ Signal Ground    │
│                      │           │                     │
│  Device 2 (String 2) │           │   RS485 Channel 2   │
│  ├─ T+ (Data+) ──────┼───────────┼──→ A                │
│  ├─ T- (Data-) ──────┼───────────┼──→ B                │
│  └─ GND ─────────────┼───────────┼──→ Signal Ground    │
│                      │           │                     │
└──────────────────────┘           └─────────────────────┘
```

### Complete System Overview

```
                    ┌─────────────────┐
                    │  24V DC Power   │
                    │  Transformer    │
                    └────────┬────────┘
                             │
                    ┌────────▼──────────────────────────┐
                    │  RS485 to Ethernet Module         │
                    │                                   │
                    │  Power: 6-36V Input, Ground       │
                    │                                   │
                    │  RS485-1: A, B, GND               │
                    │  RS485-2: A, B, GND               │
                    │                                   │
                    │  Ethernet: ETH1 or ETH2 ────────► To Network
                    │                                   │
                    └──────┬─────────────┬──────────────┘
                           │             │
                 ┌─────────▼─────┐   ┌───▼────────────┐
                 │ Thermostat    │   │ Thermostat     │
                 │ String 1      │   │ String 2       │
                 │ (via Modbus)  │   │ (via Modbus)   │
                 └───────────────┘   └────────────────┘
```

## Installation Steps

### 1. Safety First

⚠️ **IMPORTANT**: Disconnect all power before beginning installation.

### 2. Power Connection

1. Locate the existing 24V DC transformer
2. Connect the module's **6-36V Input** terminal to the transformer's **+ (positive)** output
3. Connect the module's **Ground** terminal to the transformer's **- (negative)** output

**Wire colors (typical)**:
- Red: +24V DC
- Black: Ground/Common

### 3. RS485 Data Connections

#### Understanding the XCOM Terminal Group

In your electrical panel's XCOM group, you'll find:
- First set of wires: RDZ HMI connections
- Following pairs: Two RS485 pairs for two strings of thermostats

#### Connection Notes

- **T+** on devices connects to **A** on the module
- **T-** on devices connects to **B** on the module
- **PE/GND** connects to **Signal Ground** on the module
- Some wires may be unmarked - verify with continuity testing

#### Wiring Each Channel

Connect each RS485 device string to one of the two module channels:

**For String 1** (any channel - e.g., RS485-1):
```
Device T+ ──→ RS485-1 A
Device T- ──→ RS485-1 B
Device GND ─→ RS485-1 Signal Ground
```

**For String 2** (remaining channel - e.g., RS485-2):
```
Device T+ ──→ RS485-2 A
Device T- ──→ RS485-2 B
Device GND ─→ RS485-2 Signal Ground
```

> **Note**: The assignment of devices to Channel 1 or Channel 2 is flexible. Choose either channel for each device string - the specific mapping doesn't matter as thermostat identification is done after discovery through the network.

### 4. Verify Connections

**Before applying power**:

1. ✅ Check continuity between Wi-SA connectors and module terminals
2. ✅ Verify correct polarity on power connections
3. ✅ Ensure RS485 wires are properly paired (A-to-A, B-to-B)
4. ✅ Confirm all ground connections are secure

### 5. Ethernet Connection

1. Connect an Ethernet cable from either **ETH1** or **ETH2** to your network switch/router
2. The second Ethernet port can be used for router cascading if needed

### 6. Power On and Test

1. Restore power to the 24V DC transformer
2. Check the module's LED indicators:

| LED | Description |
|-----|-------------|
| **PWR** | Power indicator - should be solid |
| **NET** | Network indicator - blinks when connected to Ethernet |
| **LINK1** | Lights up when establishing RS485 Channel 1 connection |
| **ACT1** | Lights up when Channel 1 is transmitting data |
| **LINK2** | Lights up when establishing RS485 Channel 2 connection |
| **ACT2** | Lights up when Channel 2 is transmitting data |

## Important Notes

- ⚠️ Use **shielded twisted pair cable** for all RS485 connections to minimize interference
- ⚠️ Maintain proper polarity: A↔A (T+), B↔B (T-), GND↔GND
- ⚠️ Power input must be within **6-36V DC** range (24V DC is typical)
- ⚠️ Either Ethernet port functions identically - choose whichever is more convenient
- ℹ️ Channel assignment is flexible - devices can be connected to either RS485-1 or RS485-2
- ℹ️ Device discovery and mapping is performed after installation via network configuration

## Troubleshooting

| Issue | Possible Solution |
|-------|------------------|
| PWR LED not lit | Check 24V DC power connections and voltage |
| NET LED not blinking | Verify Ethernet cable and network connection |
| LINK LED not lit | Check RS485 wiring polarity (A, B, GND) |
| No device communication | Verify continuity of RS485 cables; check for proper termination |

## Post-Installation

After successful installation:

1. Access the module's web interface via its IP address
2. Configure network settings if necessary
3. Perform device discovery to identify all connected Modbus devices
4. Map thermostats/devices to their physical locations
5. Test communication with each device

## Safety and Compliance

- Installation should be performed by a **qualified electrician**
- Follow all local electrical codes and regulations
- Ensure proper grounding of all equipment
- Use appropriate wire gauges for the application

## Additional Resources

- Consult the module's technical documentation for advanced configuration
- Refer to device-specific manuals for RS485 settings (baud rate, parity, etc.)

---

**Revision**: 1.0  
**Last Updated**: January 2026