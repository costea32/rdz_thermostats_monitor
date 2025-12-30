# Modbus RTU Monitor Integration - Development Guide

## Overview

This integration provides **passive monitoring** of Modbus RTU communication over TCP connections. It listens to existing Modbus traffic between a gateway and slave devices (e.g., thermostats) and creates Home Assistant entities based on discovered data.

**Key Feature**: Non-intrusive monitoring - the integration does not initiate Modbus requests, it only observes traffic. The exception is the climate entity's setpoint write functionality.

## Use Case & Background

This integration was developed to enable remote control and monitoring of proprietary thermostats that are integrated into a complex PLC-based heat automation system via Modbus RTU.

### Real-World Scenario

**Current Setup**:
- Multiple proprietary thermostats connected via 2 Modbus RTU lines
- Complex PLC (Programmable Logic Controller) manages heat automation
- PLC writes configuration registers to thermostats (time, mode, pump status)
- PLC reads sensor data from thermostats (temperature, humidity, setpoint)

**Challenges**:
- Proprietary thermostats with no native Home Assistant support
- Cannot interrupt or interfere with critical PLC communication
- Need to read temperature/humidity and set setpoint remotely
- Existing automation must continue functioning during transition

**Solution Approach**:
- **Passive monitoring**: Observe PLC ↔ thermostat communication without disruption
- **Selective writes**: Only write setpoint when user changes it in HA
- **Gradual migration path**: Enables Home Assistant integration while PLC continues operating
- **Future goal**: Eventually replace PLC entirely with Home Assistant automations

### Why Passive Monitoring Matters

The PLC continuously communicates with thermostats to:
- Synchronize time (hour/minute registers)
- Set operating modes (summer/winter mode)
- Control heat pump status (zone pump register 211)
- Read temperature, humidity, and manual mode setpoint

**Critical**: Any polling or active queries from Home Assistant could:
- Disrupt time-sensitive PLC communication
- Cause Modbus bus contention
- Potentially confuse the PLC or thermostats
- Create unpredictable heating behavior

**Passive monitoring solves this** by only observing existing traffic, making the integration completely invisible to the PLC and thermostats (except for explicit setpoint writes initiated by users).

### Migration Strategy

1. **Phase 1** (Current): Passive monitoring + manual setpoint control
   - Read all sensor data (temp, humidity, registers)
   - Allow manual temperature adjustment from HA
   - PLC continues all automation logic

2. **Phase 2** (Future): Gradual automation takeover
   - Start replacing PLC automations with HA automations
   - Monitor additional registers to understand PLC logic
   - Test HA automations alongside PLC

3. **Phase 3** (Goal): Full HA control
   - HA handles all heating automation
   - PLC decommissioned or relegated to backup role
   - Complete integration with HA ecosystem

This integration is the foundation for this migration path.

## Architecture

### Core Components

1. **hub.py** - Central communication hub
   - Manages TCP connection to Modbus gateway
   - Passively decodes Modbus RTU frames
   - Handles reconnection logic for extended outages
   - Provides active write capability for setpoint changes

2. **coordinator.py** - Data update coordinator
   - Manages entity updates efficiently
   - Uses throttled updates (5-second minimum interval)
   - Coordinates between hub and entity platforms

3. **Entity Platforms**:
   - **climate.py** - Thermostat control with HVAC action display
   - **sensor.py** - Humidity and register monitoring
   - **binary_sensor.py** - Coil states and zone pump status

4. **const.py** - Constants and data models
   - Register addresses and ranges
   - SlaveData and ModbusRTUFrame dataclasses
   - User-friendly register name mappings

## Critical Implementation Details

### Reconnection Logic (CRITICAL)

The integration must handle extended server outages (1-4+ hours) gracefully:

**Key Requirements**:
1. **Monitor task is always created** - even if initial connection fails (hub.py lines 198-220)
2. Always null `_reader` and `_writer` after failed reconnection attempts
3. Check `if self._reader is None:` before attempting to read
4. Exception handler must detect connection errors and trigger reconnection
5. Buffer must be cleared after reconnection attempts
6. Reconnection delay is 30 seconds (prevents DDOS during outages)

**Files**: hub.py lines 198-333

**Why This Matters**:
- Without the monitor task being always created, integrations loaded while server is down never attempt reconnection
- Without proper state management, the integration enters an infinite error loop after the first failed reconnection
- Both scenarios require manual reload without these fixes

**Critical Design Decision**:
- The monitor task handles ALL connection logic (hub.py:254-285)
- `async_setup()` only creates tasks, never attempts connection directly (hub.py:198-212)
- This prevents race conditions between setup and reconnection logic
- First connection attempt is immediate (no delay)
- Subsequent reconnection attempts use 30-second delay to prevent DDOS

### Passive Monitoring Pattern

The integration monitors three types of Modbus traffic:

1. **Temperature/Humidity** (Register 0x83, 4 registers)
   - Detected when request matches TEMP_HUMIDITY_REGISTER
   - Response contains temperature (index 2) and humidity (index 3)
   - Values divided by 10 for actual reading

2. **Coils** (Function code 0x01, 40 coils starting at address 1)
   - Binary states (ON/OFF)
   - Disabled by default (user can enable)

3. **Register Ranges** (Function code 0x03):
   - Range 1: 165-184 (20 registers) - REGISTER_START_ADDRESS
   - Range 2: 210-217 (8 registers) - REGISTER_START_ADDRESS_2
   - Range 3: 140-162 (23 registers) - REGISTER_START_ADDRESS_3

**Pattern**: Hub detects request frames, stores pending request data, then matches response frames to extract values.

### Register Name Mapping

User-friendly names are maintained in `const.py` REGISTER_NAMES dictionary:

```python
REGISTER_NAMES: dict[int, str] = {
    144: "Setpoint",              # Target temperature (written by PLC or HA)
    145: "Max Setpoint",           # Maximum allowed temperature
    146: "Min Setpoint",           # Minimum allowed temperature
    154: "Hour",                   # Current hour (synchronized by PLC)
    155: "Minute",                 # Current minute (synchronized by PLC)
    156: "Day of week",            # Current day (synchronized by PLC)
    157: "Current temperature",    # Actual temperature reading
    179: "Outside temperature",    # External temperature sensor
    211: "Zone pump",              # Heat pump/zone valve status (1=ON, 0=OFF)
}
```

**PLC-Written Registers**: The PLC writes registers 154-156 (time sync) and 211 (pump control). These are monitored to understand system state but should not be written by HA while the PLC is active.

**HA-Writable Register**: Register 144 (Setpoint) can be safely written by Home Assistant when users adjust temperature, as this mimics manual thermostat adjustment.

**To add new mappings**: Update REGISTER_NAMES in const.py - sensor entities will automatically use friendly names. As you discover more registers through monitoring, document their purpose here.

### Climate Entity Bidirectional Sync

The climate entity maintains setpoint synchronization in both directions:

1. **User sets temperature in HA**:
   - Climate entity writes to device via hub.async_write_setpoint()
   - Immediately updates coordinator data to prevent UI flicker
   - Scaled value (temp × 10) written to register 144

2. **Physical thermostat changes setpoint**:
   - Hub passively monitors register 144
   - Climate entity reads from coordinator.data[slave_id].registers[144]
   - Scales value (÷ 10) for display

**Key Detail**: Register 144 value is immediately updated after write to prevent UI from showing stale value until next monitoring cycle.

### HVAC Action Display

Climate entity shows heating status based on register 211:
- `HVACAction.HEATING` when register 211 = 1
- `HVACAction.IDLE` when register 211 = 0 or unavailable

**Dual Representation**: Register 211 exists as both:
- Regular sensor showing raw integer value (disabled by default)
- Binary sensor "Zone pump" showing ON/OFF state (enabled by default)

This allows users to choose their preferred representation.

### Entity Default States

- **Enabled by default**: Humidity sensor, zone pump binary sensor, climate entity
- **Disabled by default**: All register sensors (except humidity), all coil sensors

Users can selectively enable the entities they need.

## Data Flow

```
Modbus Gateway ←→ TCP Connection ←→ Hub (passive monitoring)
                                      ↓ (frames decoded)
                                  discovered_slaves dict
                                      ↓ (throttled updates)
                                  Coordinator
                                      ↓
                            Entity Platforms (climate, sensor, binary_sensor)
```

### Update Throttling

**Coordinator Updates**: Minimum 5-second interval between updates
- Defined in COORDINATOR_UPDATE_INTERVAL
- Prevents overwhelming Home Assistant with high-frequency Modbus traffic
- Hub calls `_update_coordinator_throttled()` which checks timing

**Why**: Modbus traffic can be very frequent (multiple times per second). Without throttling, HA UI becomes sluggish.

## Connection Handling

### Multiple Servers

Users can configure multiple Modbus gateways as separate config entries. Each entry creates its own:
- Hub instance with dedicated TCP connection
- Monitor task
- Set of discovered slaves and entities

**Important**: 30-second reconnection delay prevents DDOS when multiple servers are offline simultaneously.

### Availability Tracking

Slaves are marked unavailable if no data received for 5 minutes (AVAILABILITY_TIMEOUT).

**Implementation**: Separate `_availability_check_loop()` runs every 60 seconds and compares `last_seen` timestamp.

## Modbus Protocol Details

### RTU Frame Structure

```
[Slave ID][Function Code][Data...][CRC Low][CRC High]
```

**CRC Calculation**: Uses Modbus RTU CRC-16 algorithm (polynomial 0xA001)

### Supported Function Codes

- **0x01**: Read Coils (request + response with bitmap)
- **0x03**: Read Holding Registers (request + response with values)
- **0x06**: Write Single Register (used for setpoint writes)

### Signed vs Unsigned Integers

Modbus uses unsigned 16-bit values, but physical readings can be negative (e.g., temperatures).

**Conversion** (hub.py):
```python
if value > 32767:
    signed_value = value - 65536
else:
    signed_value = value
```

This converts unsigned to signed int16 representation.

## Common Development Tasks

### Adding New Register Mappings

1. Identify register address and purpose through monitoring
2. Update `REGISTER_NAMES` in const.py:
   ```python
   REGISTER_NAMES: dict[int, str] = {
       # ... existing mappings ...
       XXX: "Your Register Name",
   }
   ```
3. Sensors automatically display friendly name

### Extending Monitored Register Ranges

To monitor additional register ranges:

1. Add constants to const.py:
   ```python
   REGISTER_START_ADDRESS_4 = 0xYY  # Your start address
   REGISTER_MONITOR_COUNT_4 = ZZ    # Number of registers
   ```

2. Update hub.py `_handle_frame()` to detect requests/responses for the new range
   - Follow pattern from existing ranges (1, 2, 3)
   - Use unique pending request key (e.g., `f"{slave_id}_registers4"`)

3. Update sensor.py `async_setup_entry()` to create sensors for new range
   - Add tracking set (e.g., `added_slaves_registers4`)
   - Add sensor creation logic in `_async_add_sensor_entities()`

### Testing Reconnection Logic

**Critical Test**: Long outage scenario
```bash
# 1. Start integration with working server
# 2. Stop Modbus server
# 3. Wait 2+ hours
# 4. Check logs - should see reconnection attempts every ~30 seconds
# 5. Start Modbus server
# 6. Verify automatic reconnection within 30 seconds
# 7. Verify data flow resumes without manual reload
```

## Known Issues and Solutions

### Issue: UI Flicker When Setting Temperature

**Symptom**: After setting temperature, UI briefly reverts to old value before updating.

**Solution**: Immediately update `slave_data.registers[SETPOINT_REGISTER]` after successful write (climate.py line 178).

### Issue: Integration Won't Reconnect After Long Outage

**Symptom**: After server outage >1 hour, integration requires manual reload.

**Root Cause**: Reader/writer not properly nulled on failed reconnection.

**Solution**: Implemented in hub.py lines 222-333 (see Reconnection Logic section above).

### Issue: Too Many Connection Attempts During Outage

**Symptom**: Server logs show connection spam when offline.

**Solution**: 30-second reconnection delay (hub.py line 237).

## Code Patterns and Conventions

### Async Safety

- All I/O operations are async
- Write operations use `self._write_lock` to prevent concurrent access
- Coordinator updates use `@callback` decorator where appropriate

### Logging

- Debug level: Frame processing details, non-critical events
- Info level: Connection status, slave discovery, successful operations
- Warning level: Connection loss, reconnection attempts
- Error level: Failed reconnections, unexpected errors

**Format**: Always include `self.host:self.port` in connection-related messages.

### Entity Registration

Entities are dynamically created when slaves are discovered:
- Use tracking sets (e.g., `added_slaves`, `added_slaves_registers`)
- Subscribe to coordinator updates via `async_add_listener()`
- Only create entities when new slaves/data detected

### Device Info

All entities for a slave share the same device:
```python
DeviceInfo(
    identifiers={(DOMAIN, f"{coordinator.config_entry.entry_id}_{slave_id}")},
    name=f"Modbus Slave {slave_id}",
    manufacturer=MANUFACTURER,
    model=MODEL,
)
```

## Configuration

**No YAML configuration** - integration uses config flow only.

**Config Entry Data**:
- `host`: Modbus gateway IP/hostname
- `port`: TCP port (default 502)

**Runtime Data**: Hub instance stored in `entry.runtime_data`

## Files Overview

- **manifest.json** - Integration metadata and dependencies
- **const.py** - Constants, register addresses, data models
- **hub.py** - TCP connection, frame decoding, reconnection logic
- **coordinator.py** - Data update coordination
- **config_flow.py** - UI configuration
- **climate.py** - Thermostat entity
- **sensor.py** - Humidity and register sensors
- **binary_sensor.py** - Coil and zone pump sensors
- **__init__.py** - Integration setup/unload

## Important Notes for AI Assistants

1. **Never remove the 30-second reconnection delay** - it prevents DDOS during outages
2. **Always clear buffer after reconnection** - prevents processing stale frames
3. **Maintain throttling** - Modbus traffic is high-frequency, HA needs protection
4. **Preserve passive monitoring** - don't add active polling unless specifically requested
5. **Keep register sensors disabled by default** - there are many, most users don't need them
6. **Test with extended outages** - this is the most common production issue

## Future Enhancements

Potential improvements to consider:
- Support for Modbus RTU over serial (currently TCP only)
- Configurable register ranges via UI
- Entity auto-discovery based on register schema files
- Diagnostic sensors for connection statistics
- Service to manually trigger reconnection
