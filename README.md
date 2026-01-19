# RDZ Thermostats Monitor

A Home Assistant custom integration for monitoring and controlling RDZ thermostats via Modbus RTU over TCP.

## Overview

This integration enables passive monitoring and control of RDZ thermostats that are connected to a PLC-based heating system via Modbus RTU. It uses a 2-Channel RS485 to Ethernet adapter to bridge the Modbus network to your local network, allowing Home Assistant to observe thermostat communication and send temperature setpoint commands.

**Key Features:**
- Passive monitoring of temperature, humidity, and thermostat status
- Remote temperature setpoint control from Home Assistant
- Automatic discovery of thermostats on the Modbus network
- Climate entities with HVAC action display (heating/idle)
- Zone pump status monitoring

### What This Enables

This integration provides **monitoring and control** of your RDZ thermostats within Home Assistant. With the zone pump status exposed, you can see exactly when each zone was heating or cooling, and Home Assistant's recorder keeps a full history of this data. The temperature and humidity readings, combined with setpoint control, open up possibilities for extending functionality through Home Assistant automations - such as granular scheduling, event-based heating (presence, weather, calendar), or using sensor values to trigger alerts and other automations. These extensions are not built into the plugin but are easily achievable using Home Assistant's native automation capabilities.

## Prerequisites

- **Home Assistant** installed and running (Core, Supervised, or OS) 
- **2-Channel RS485 to Ethernet adapter** ([Waveshare](https://amzn.to/49rCdDc) or compatible)
- **RDZ thermostats** connected via Modbus RTU
- Basic networking knowledge

## Bill of Materials

| Item | Description | Quantity | Notes                                                                                             |
|------|-------------|----------|---------------------------------------------------------------------------------------------------|
| RS485 to Ethernet Adapter | 2-CH RS485 to ETH (B) | 1 | [Waveshare](https://amzn.to/49rCdDc) or similar (Configuration Steps refer to this specific model) |
| 24V DC Power Supply | 6-36V DC compatible | 1 | May use existing transformer or [MEAN WELL](https://amzn.to/3Nz7kUI)                              |
| Ethernet Cable | Cat5e or better | 1 | To connect adapter to network                                                                     |
| RS485 Cable | Shielded twisted pair | As needed | For RS485 connections                                                                             |
| Home Assistant | if you don't already have it, the host on which the plugin will run | 1| [Pre Built](https://amzn.to/4qEBK6w) or you can DIY with RPI, or other solutions |
## Installation

### 1. Hardware Setup

Follow the detailed hardware installation guide:

**[Hardware Installation Instructions](2ch%20RS485%20Hardware%20Installation%20Instructions.md)**

This covers:
- Power connections (24V DC)
- RS485 wiring (A, B, GND terminals)
- Ethernet network connection
- LED indicator verification

### 2. RS485 Adapter Configuration

Configure the RS485 to Ethernet adapter:

**[Software Configuration Guide](2ch%20RS485%20Software%20Configuration.md)**

Key settings you'll need for Home Assistant:
- **IP Address**: Note down the IP you assign (e.g., `192.168.11.200`)
- **Port**: Default is `4196`
- **Baud Rate**: Must be `19200`

### 3. Home Assistant Integration Setup

#### Copy the Integration

1. Download or clone this repository
2. Copy the `custom_components/rdz_thermostats_monitor/` folder to your Home Assistant's `custom_components/` directory:

```
/config/custom_components/rdz_thermostats_monitor/
```

Your directory structure should look like:
```
/config/
├── configuration.yaml
├── custom_components/
│   └── rdz_thermostats_monitor/
│       ├── __init__.py
│       ├── manifest.json
│       ├── climate.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       └── ...
```

#### Restart Home Assistant

Restart Home Assistant to load the new integration:
- Go to **Settings** > **System** > **Restart**
- Or use the command line: `ha core restart`

#### Add the Integration

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"RDZ Thermostats Monitor"**
4. Enter the configuration:
   - **Host**: IP address of your RS485 adapter (e.g., `192.168.11.200`)
   - **Port**: TCP port (default: `4196`)
5. Click **Submit**

**Note**: If you have two RS485 channels (two thermostat strings), add the integration twice - once for each channel's IP address.

#### Verify Setup

After adding the integration:
1. Thermostats will be automatically discovered as they communicate
2. Each thermostat appears as a device named "RDZ Thermostat X" (where X is the Modbus slave ID)
3. Entities created include:
   - `climate.rdz_thermostat_X` - Main thermostat control
   - `sensor.rdz_thermostat_X_humidity` - Humidity reading
   - `binary_sensor.rdz_thermostat_X_zone_pump` - Zone pump status

## Configuration Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| Host | IP address of RS485 adapter | Required |
| Port | TCP port for Modbus communication | 4196 |

## Disclaimer - Secondary Master Communication

**Important:** This integration operates as a **secondary Modbus master** on the RS485 bus. The primary master is typically your PLC or building automation system.

### What This Means

When you change a temperature setpoint in Home Assistant, this integration sends commands to the thermostat. However, since the PLC is continuously communicating with the thermostats, there's a possibility of **bus contention** - where both masters try to communicate simultaneously.

### Potential Issues

- **Command conflicts**: Occasionally, setpoint commands from Home Assistant may not be received correctly by the thermostat due to timing conflicts with PLC communication
- **Intermittent failures**: While rare, you may notice that a temperature change doesn't "stick" on the first attempt

### Mitigation Strategies

1. **Retry mechanism**: The integration includes automatic retry logic (5 attempts with 1.3-second intervals) to increase command success rate

2. **Consistent updates**: If you're using automations to set temperatures, consider pushing the desired setpoint multiple times or verifying the setpoint was accepted:

```yaml
# Example: Automation with verification
automation:
  - alias: "Set morning temperature with retry"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - repeat:
          count: 3
          sequence:
            - service: climate.set_temperature
              target:
                entity_id: climate.rdz_thermostat_1
              data:
                temperature: 21
            - delay: "00:00:05"
```

3. **Monitor for changes**: Use the climate entity's `current_temperature` and `temperature` (setpoint) attributes to verify commands were accepted

### Why This Happens

The Modbus RTU protocol doesn't natively support multiple masters. This integration works by:
- Passively monitoring existing PLC-thermostat traffic (read-only, no conflicts)
- Only actively transmitting when you change a setpoint (potential for brief conflicts)

In practice, conflicts are **rare** and the retry mechanism handles most cases automatically.

## Troubleshooting

### No Thermostats Discovered

- Verify the RS485 adapter is powered (PWR LED lit)
- Check network connectivity (ping the adapter's IP)
- Confirm baud rate is set to 19200
- Check RS485 wiring polarity (A to A, B to B)

### Thermostats Show as Unavailable

- Ensure the PLC/primary master is communicating with thermostats
- Check the adapter's ACT LEDs for data transmission activity
- Verify the integration is connected (check Home Assistant logs)

### Setpoint Changes Don't Apply

- This may be due to bus contention (see Disclaimer above)
- Try changing the setpoint again
- Check Home Assistant logs for error messages

### View Logs

Enable debug logging to troubleshoot:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.rdz_thermostats_monitor: debug
```

## Support

For issues and feature requests, please open an issue on the GitHub repository.

## License

This project is provided as-is for personal use. See LICENSE file for details.

---

**Version**: 1.0.0
**Last Updated**: January 2026