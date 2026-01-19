# RS485 to Ethernet Module - Software Configuration Guide

## Overview

This guide covers the essential software configuration of the 2-CH RS485 to Ethernet adapter. Configuration is done via web browser - no software installation required.

## What You Need to Configure

**Only two things are critical:**
1. **IP Address** - Match your network
2. **Baud Rate** - Set to 19200 (or match your devices)

All other settings can remain at their defaults.

## Quick Start

### Default Module Settings

- **Channel 1**: `192.168.1.200`
- **Channel 2**: `192.168.1.201`
- **Default Port**: `4196`
- **No password required** (first login)

### Step 1: Access the Web Interface

1. Temporarily set your computer's IP to `192.168.1.100` (same network as module)
2. Open web browser and go to:
   - Channel 1: `http://192.168.1.200`
   - Channel 2: `http://192.168.1.201`
3. Click "Login" (leave password blank on first access)

### Step 2: Change IP Address

**Network Settings section:**
- **Device IP**: Change to your network (example: `192.168.11.200`)
- **Subnet Mask**: Usually `255.255.255.0`
- **Gateway**: Your router IP (example: `192.168.11.1`)
- Leave other settings as default

> **Important**: Each channel needs a unique IP! Use sequential IPs like `.200` and `.201`

### Step 3: Set Baud Rate

**Serial Settings section:**
- **Baud Rate**: Set to `19200`
- Leave other serial settings as default (8 databits, None parity, 1 stopbit)

### Step 4: Save and Repeat

1. Click **"Submit Modification"**
2. Access the module at its new IP address
3. Repeat Steps 1-4 for Channel 2 with a different IP

## Configuration Summary

### Essential Settings to Change

| Setting | Channel 1 | Channel 2 |
|---------|-----------|-----------|
| **Device IP** | `192.168.x.200` | `192.168.x.201` |
| **Baud Rate** | `19200` | `19200` |

### Other Settings (Keep Defaults)

The web interface shows additional settings that can remain at defaults:
- Work Mode: TCP Server
- Device Port: 4196
- IP mode: Static
- Databits: 8
- Parity: None
- Stopbits: 1
- Flow control: None
- Advanced Settings: Keep defaults
- Multi-Host Settings: Keep defaults

## LED Indicators

After configuration, check the module's LEDs:

| LED | Expected Status |
|-----|----------------|
| **PWR** | Solid (power on) |
| **NET** | Blinking (network connected) |
| **LINK1/2** | On (RS485 connection) |
| **ACT1/2** | Blinking (data transmission) |

## Troubleshooting

### Can't Access Web Interface

1. Verify your computer is on `192.168.1.x` network
2. Check Ethernet cable is connected
3. Ensure module is powered (PWR LED lit)
4. **Reset if needed**: Hold RESET button for 5 seconds (reverts to `192.168.1.254`)

### Can't Access After Changing IP

1. Update your computer's IP to match the new network
2. Verify gateway and subnet mask are correct
3. If lost, reset module and start over

### No RS485 Communication

1. Verify baud rate is set to `19200`
2. Check RS485 wiring: A to A (T+), B to B (T-)
3. Ensure RS485 devices are powered

## Configuration Checklist

- [ ] Accessed Channel 1 web interface (`192.168.1.200`)
- [ ] Changed Channel 1 IP to match my network
- [ ] Set Channel 1 baud rate to `19200`
- [ ] Saved and verified Channel 1 settings
- [ ] Accessed Channel 2 web interface (`192.168.1.201`)
- [ ] Changed Channel 2 IP to match my network (unique from Channel 1)
- [ ] Set Channel 2 baud rate to `19200`
- [ ] Saved and verified Channel 2 settings
- [ ] Verified LED indicators are working

## Example Configuration

Based on network `192.168.11.x`:

**Channel 1** (`http://192.168.11.200`):
```
Device IP:      192.168.11.200
Baud Rate:      19200
Subnet Mask:    255.255.255.0
Gateway:        192.168.11.1
```

**Channel 2** (`http://192.168.11.201`):
```
Device IP:      192.168.11.201
Baud Rate:      19200
Subnet Mask:    255.255.255.0
Gateway:        192.168.11.1
```

---

**For Additional Help**:
- **Waveshare Wiki**: https://www.waveshare.com/wiki/2-CH_RS485_TO_ETH_(B)
- **Support**: Contact us for configuration assistance

**Last Updated**: January 2026