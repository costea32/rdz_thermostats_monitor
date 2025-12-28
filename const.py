"""Constants for the Modbus RTU Monitor integration."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

DOMAIN = "modbus_rtu_monitor"

# Default values
DEFAULT_PORT = 502

# Modbus register configuration
TEMP_HUMIDITY_REGISTER = 0x83  # Register 131 (decimal)
SETPOINT_REGISTER = 144  # Register 144 (decimal, 0x90 hex)
HEATING_STATUS_REGISTER = 211  # Register 211
REGISTER_COUNT = 4

# Register name mapping for user-friendly display in Home Assistant
# Add new register names here as you discover them
# Format: register_number: "Friendly Name"
REGISTER_NAMES: dict[int, str] = {
    # Known registers
    144: "Setpoint",
    145: "Max Setpoint",
    146: "Min Setpoint",
    154: "Hour",
    155: "Minute",
    156: "Day of week",
    157: "Current temperature",
    179: "Outside temperature",
    211: "Heating status",
    # Add more registers as discovered
    # Example:
    # 165: "Register name",
    # 166: "Another register",
}

# Coil configuration
COIL_START_ADDRESS = 0x01  # Starting coil address (1 in decimal)
COIL_COUNT = 40  # Number of coils to monitor

# Register monitoring configuration
REGISTER_START_ADDRESS = 0xA5  # Register 165 (decimal)
REGISTER_MONITOR_COUNT = 20  # Number of registers to monitor (165-184)

# Additional register monitoring
REGISTER_START_ADDRESS_2 = 0xD2  # Register 210 (decimal)
REGISTER_MONITOR_COUNT_2 = 8  # Number of registers to monitor (210-217)

# Third register range
REGISTER_START_ADDRESS_3 = 0x8C  # Register 140 (decimal)
REGISTER_MONITOR_COUNT_3 = 23  # Number of registers to monitor (140-162)

# Availability timeout (if no data for 5 minutes, mark unavailable)
AVAILABILITY_TIMEOUT = timedelta(minutes=5)

# Update throttling (prevent overwhelming HA with high-frequency Modbus traffic)
COORDINATOR_UPDATE_INTERVAL = timedelta(seconds=5)  # Minimum time between coordinator updates
FRAME_PROCESSING_DELAY = 0.1  # Seconds to sleep between frame processing batches

# Device info
MANUFACTURER = "Modbus RTU"
MODEL = "Temperature/Humidity Monitor"


@dataclass
class SlaveData:
    """Data for a discovered Modbus slave."""

    slave_id: int
    temperature: float | None
    humidity: float | None
    last_seen: datetime
    available: bool = True
    coils: list[bool] | None = None  # 40 coil states (True=ON, False=OFF)
    registers: dict[int, int] | None = None  # Register address -> int16 value
    setpoint: float | None = None  # Target temperature setpoint (°C)


@dataclass
class ModbusRTUFrame:
    """Decoded Modbus RTU frame."""

    slave_id: int
    function_code: int
    data: bytes
    is_request: bool
    is_response: bool
    start_address: int | None = None
    register_count: int | None = None
    values: list[int] | None = None
    coil_values: list[bool] | None = None  # For function code 01 (Read Coils) responses
