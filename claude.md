# RDZ Thermostats Monitor - Development Repository

## Overview

This repository contains the **RDZ Thermostats Monitor** custom integration for Home Assistant, along with a complete development environment for local testing.

**Integration Purpose**: Passive monitoring of Modbus RTU communication over TCP, enabling Home Assistant control of RDZ thermostats in a PLC-based heating system without disrupting existing automation.

## Repository Structure

```
modbus_rtu_monitor/                      # This repository
├── .devcontainer/
│   └── devcontainer.json               # Dev container for local HA testing
├── config/                             # HA configuration for dev environment
│   ├── configuration.yaml              # Minimal HA config
│   └── custom_components/              # Mount point during development
├── custom_components/
│   └── rdz_thermostats_monitor/       # THE INTEGRATION (publish this folder)
│       ├── claude.md                  # 📋 DETAILED INTEGRATION DOCS HERE
│       ├── __init__.py
│       ├── hub.py
│       ├── coordinator.py
│       ├── climate.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── config_flow.py
│       ├── const.py
│       ├── manifest.json
│       └── strings.json
└── claude.md                          # This file (repo overview)
```

## Quick Start (Development)

### Using Dev Container

1. **Open in IDE with dev container support** (VS Code or IntelliJ IDEA)
2. **Container builds automatically** and installs Home Assistant
3. **Start HA**:
   ```bash
   hass -c /config --debug
   ```
4. **Access UI** at http://localhost:8123
5. **Edit code** in `custom_components/rdz_thermostats_monitor/`
6. **Restart HA** to test changes (Ctrl+C, then rerun `hass`)

### Dev Container Details

The `.devcontainer/devcontainer.json` provides:
- Python 3.12 environment
- Auto-installed Home Assistant
- Live code mounting (no rebuild needed)
- Port 8123 forwarded to host
- IntelliJ IDEA integration

## Documentation

### 📋 Integration Documentation

**For detailed integration documentation, implementation details, and development guides, see:**

**[`custom_components/rdz_thermostats_monitor/claude.md`](custom_components/rdz_thermostats_monitor/claude.md)**

That file contains:
- Integration architecture and design patterns
- Critical implementation details (reconnection logic, passive monitoring)
- Modbus protocol specifics
- Development tasks and testing procedures
- Code patterns and conventions
- Known issues and solutions

### Repository vs Integration

This repository serves two purposes:

1. **Development Environment** (root level)
   - Dev container configuration
   - Local HA instance for testing
   - This file documents the dev setup

2. **Home Assistant Integration** (`custom_components/rdz_thermostats_monitor/`)
   - The actual integration code
   - Published/installed to HA's `custom_components/` folder
   - See nested `claude.md` for integration details

## Installation (Production)

To install this integration in a production Home Assistant instance:

1. Copy the **entire** `custom_components/rdz_thermostats_monitor/` folder to your HA's `custom_components/` directory
2. Restart Home Assistant
3. Add the integration via UI: Settings → Devices & Services → Add Integration → "RDZ Thermostats Monitor"

## Key Features

- **Passive Monitoring**: Observes existing Modbus traffic without interfering
- **No Polling**: Completely non-intrusive to PLC communication
- **Auto-Discovery**: Automatically creates entities for discovered slaves
- **Robust Reconnection**: Handles extended server outages gracefully
- **Selective Writing**: Only writes setpoint when user changes temperature
- **Climate Entity**: Full thermostat control with HVAC action display
- **Configurable**: Enable only the sensors you need

## Technology Stack

- **Home Assistant**: Smart home automation platform
- **Modbus RTU over TCP**: Industrial communication protocol
- **Python 3.12**: Integration implementation language
- **Dev Containers**: Isolated development environment

## Use Case

This integration enables remote monitoring and control of RDZ thermostats in a PLC-based heating system, providing a migration path from PLC automation to Home Assistant without disrupting existing critical infrastructure.

For full background and use case details, see the [integration documentation](custom_components/rdz_thermostats_monitor/claude.md#use-case--background).

## Support & Contribution

When working on this integration:
- Always consult `custom_components/rdz_thermostats_monitor/claude.md` for implementation details
- Test with the dev container before deploying to production
- Maintain passive monitoring approach (no active polling)
- Test reconnection logic with extended outages

## File Organization

- **Root `claude.md`** (this file): Repository overview, dev environment setup
- **Integration `claude.md`**: Detailed implementation docs, architecture, protocols
- **`.devcontainer/`**: Development environment configuration
- **`config/`**: HA configuration for local testing
- **`custom_components/rdz_thermostats_monitor/`**: The integration itself (publishable)