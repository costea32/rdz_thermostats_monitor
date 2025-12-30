"""Modbus RTU Monitor Hub for passive monitoring and active writes."""

from __future__ import annotations

import asyncio
import logging
import struct
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.util.dt import utcnow

from .const import (
    AVAILABILITY_TIMEOUT,
    COIL_COUNT,
    COIL_START_ADDRESS,
    COORDINATOR_UPDATE_INTERVAL,
    DOMAIN,
    FRAME_PROCESSING_DELAY,
    REGISTER_COUNT,
    REGISTER_MONITOR_COUNT,
    REGISTER_MONITOR_COUNT_2,
    REGISTER_MONITOR_COUNT_3,
    REGISTER_START_ADDRESS,
    REGISTER_START_ADDRESS_2,
    REGISTER_START_ADDRESS_3,
    SETPOINT_REGISTER,
    TEMP_HUMIDITY_REGISTER,
    ModbusRTUFrame,
    SlaveData,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import ModbusRTUMonitorCoordinator

_LOGGER = logging.getLogger(__name__)


class ModbusRTUDecoder:
    """Decode Modbus RTU frames."""

    @staticmethod
    def calculate_crc(data: bytes) -> int:
        """Calculate Modbus RTU CRC."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    @staticmethod
    def build_write_register_frame(slave_id: int, register: int, value: int) -> bytes:
        """Build a Modbus RTU Write Single Register frame (function code 0x06).

        Args:
            slave_id: Modbus slave ID (1-247)
            register: Register address (0-65535)
            value: Register value to write (0-65535)

        Returns:
            Complete RTU frame with CRC
        """
        # Function code 0x06 = Write Single Register
        frame = bytearray()
        frame.append(slave_id)
        frame.append(0x06)  # Function code
        frame.extend(struct.pack(">H", register))  # Register address (big-endian)
        frame.extend(struct.pack(">H", value))  # Register value (big-endian)

        # Calculate and append CRC (little-endian)
        crc = ModbusRTUDecoder.calculate_crc(bytes(frame))
        frame.extend(struct.pack("<H", crc))

        return bytes(frame)

    @staticmethod
    def decode_frame(data: bytes) -> ModbusRTUFrame | None:
        """Decode a Modbus RTU frame."""
        if len(data) < 4:
            return None

        slave_id = data[0]
        function_code = data[1]
        frame_data = data[2:-2]
        received_crc = struct.unpack("<H", data[-2:])[0]
        calculated_crc = ModbusRTUDecoder.calculate_crc(data[:-2])

        if received_crc != calculated_crc:
            return None

        decoded = ModbusRTUFrame(
            slave_id=slave_id,
            function_code=function_code,
            data=frame_data,
            is_request=False,
            is_response=False,
        )

        # Detect request (function 1, Read Coils - with address and count)
        if function_code == 1 and len(frame_data) == 4:
            start_addr = struct.unpack(">H", frame_data[0:2])[0]
            count = struct.unpack(">H", frame_data[2:4])[0]
            decoded.is_request = True
            decoded.start_address = start_addr
            decoded.register_count = count

        # Detect response (function 1, Read Coils - with byte count and coil values)
        elif function_code == 1 and len(frame_data) > 1:
            byte_count = frame_data[0]
            if len(frame_data) >= byte_count + 1:
                # Decode coil bitmap
                coil_values = []
                for byte_idx in range(byte_count):
                    byte_val = frame_data[byte_idx + 1]
                    # Each byte contains 8 coil states (LSB first)
                    for bit_idx in range(8):
                        coil_values.append(bool(byte_val & (1 << bit_idx)))
                decoded.is_response = True
                decoded.coil_values = coil_values

        # Detect request (function 3, with address and count)
        elif function_code == 3 and len(frame_data) == 4:
            start_addr = struct.unpack(">H", frame_data[0:2])[0]
            count = struct.unpack(">H", frame_data[2:4])[0]
            decoded.is_request = True
            decoded.start_address = start_addr
            decoded.register_count = count

        # Detect response (function 3, with byte count and values)
        elif function_code == 3 and len(frame_data) > 1:
            byte_count = frame_data[0]
            if len(frame_data) >= byte_count + 1:
                values = []
                for i in range(0, byte_count, 2):
                    if i + 1 < byte_count:
                        val = struct.unpack(">H", frame_data[i + 1 : i + 3])[0]
                        values.append(val)
                decoded.is_response = True
                decoded.values = values

        return decoded


class ModbusRTUMonitorHub:
    """Hub for passive Modbus RTU monitoring and active writes."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, host: str, port: int
    ) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.config_entry = config_entry
        self.host = host
        self.port = port

        # Asyncio TCP connection
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._monitor_task: asyncio.Task | None = None

        # Coordination lock for write operations
        self._write_lock = asyncio.Lock()

        # Slave discovery and state
        self.discovered_slaves: dict[int, SlaveData] = {}
        self._pending_requests: dict[int | str, dict] = {}

        # Frame decoder
        self._decoder = ModbusRTUDecoder()

        # Coordinator reference (set after initialization)
        self.coordinator: ModbusRTUMonitorCoordinator | None = None

        # Availability check task
        self._availability_task: asyncio.Task | None = None

        # Throttling for coordinator updates
        self._last_coordinator_update = utcnow() - COORDINATOR_UPDATE_INTERVAL

    def _should_update_coordinator(self) -> bool:
        """Check if enough time has passed to update the coordinator."""
        return (utcnow() - self._last_coordinator_update) >= COORDINATOR_UPDATE_INTERVAL

    def _update_coordinator_throttled(self) -> None:
        """Update coordinator with throttling to prevent overwhelming HA."""
        if self.coordinator and self._should_update_coordinator():
            self.coordinator.async_set_updated_data(self.discovered_slaves)
            self._last_coordinator_update = utcnow()

    async def async_setup(self) -> bool:
        """Set up the hub and start monitoring."""
        # Start monitor and availability tasks
        # The monitor loop handles all connection logic (initial and reconnections)
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._availability_task = asyncio.create_task(
            self._availability_check_loop()
        )

        _LOGGER.info(
            "Modbus RTU Monitor hub starting for %s:%s (monitor task will establish connection)",
            self.host,
            self.port,
        )
        return True

    async def _connect(self) -> None:
        """Connect or reconnect to Modbus gateway."""
        # Close existing connection if present
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as ex:
                _LOGGER.debug("Error closing writer: %s", ex)

        # Null out reader/writer
        self._reader = None
        self._writer = None

        # Attempt connection
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=30.0,
            )
            _LOGGER.info("Connected to Modbus gateway at %s:%s", self.host, self.port)
        except Exception as ex:
            _LOGGER.warning(
                "Connection failed for %s:%s - %s (will retry)",
                self.host,
                self.port,
                ex,
            )
            # Reader/writer are already None, will retry on next iteration

    async def _monitor_loop(self) -> None:
        """Main monitoring loop for passive frame reception."""
        buffer = bytearray()

        while True:
            try:
                # Check if reader is valid before attempting to read
                if self._reader is None:
                    _LOGGER.info("Attempting connection to %s:%s", self.host, self.port)
                    await self._connect()
                    buffer.clear()
                    continue

                # Read with 30-second timeout (includes reconnection delay)
                data = await asyncio.wait_for(self._reader.read(1024), timeout=30.0)

                if not data:
                    # Connection closed gracefully
                    _LOGGER.warning("Connection closed to %s:%s, reconnecting", self.host, self.port)
                    await self._connect()
                    buffer.clear()
                    continue

                buffer.extend(data)

                # Process frames from buffer (limit iterations to prevent blocking)
                max_iterations = 100
                iterations = 0
                while len(buffer) >= 4 and iterations < max_iterations:
                    frame_found = False

                    # Try different frame lengths
                    for frame_len in range(4, min(len(buffer) + 1, 256)):
                        potential_frame = bytes(buffer[:frame_len])
                        decoded = self._decoder.decode_frame(potential_frame)

                        if decoded:
                            await self._handle_frame(decoded)
                            buffer = buffer[frame_len:]
                            frame_found = True
                            break

                    if not frame_found:
                        # Invalid data, discard first byte
                        buffer = buffer[1:]

                    iterations += 1

                # If we hit the iteration limit, yield to event loop
                if iterations >= max_iterations and len(buffer) >= 4:
                    await asyncio.sleep(0)  # Yield control to event loop

                # Rate limiting: sleep after processing to avoid overwhelming HA
                if iterations > 0:
                    await asyncio.sleep(FRAME_PROCESSING_DELAY)

            except asyncio.TimeoutError:
                # No data for 30 seconds - connection dead, reconnect directly
                _LOGGER.warning(
                    "Read timeout after 30 seconds on %s:%s - connection dead, reconnecting",
                    self.host,
                    self.port,
                )
                await self._connect()
                buffer.clear()
                continue
            except asyncio.CancelledError:
                break
            except (AttributeError, OSError, ConnectionError) as ex:
                # Connection-related errors - trigger reconnection
                _LOGGER.warning(
                    "Connection error in monitor loop for %s:%s - %s (will reconnect)",
                    self.host,
                    self.port,
                    ex,
                )
                # Null out connection and trigger reconnect
                self._reader = None
                self._writer = None
                await self._connect()
                buffer.clear()
                continue
            except Exception as ex:
                # Other unexpected errors
                _LOGGER.error("Unexpected error in monitor loop for %s:%s - %s", self.host, self.port, ex)
                await asyncio.sleep(5)

    async def _handle_frame(self, frame: ModbusRTUFrame) -> None:
        """Handle a decoded Modbus RTU frame."""
        slave_id = frame.slave_id

        # Detect Read Coils request (function 01)
        if (
            frame.is_request
            and frame.function_code == 1
            and frame.start_address == COIL_START_ADDRESS
            and frame.register_count == COIL_COUNT
        ):
            self._pending_requests[f"{slave_id}_coils"] = {
                "timestamp": utcnow(),
                "slave_id": slave_id,
                "type": "coils",
            }

        # Handle Read Coils response
        elif (
            frame.is_response
            and frame.function_code == 1
            and f"{slave_id}_coils" in self._pending_requests
            and frame.coil_values
        ):
            # Ensure slave exists
            if slave_id not in self.discovered_slaves:
                _LOGGER.info("Discovered new slave via coils: %s", slave_id)
                self.discovered_slaves[slave_id] = SlaveData(
                    slave_id=slave_id,
                    temperature=None,
                    humidity=None,
                    last_seen=utcnow(),
                    available=False,
                )

            # Update coil data (limit to COIL_COUNT coils)
            slave_data = self.discovered_slaves[slave_id]
            slave_data.coils = frame.coil_values[:COIL_COUNT]
            slave_data.last_seen = utcnow()
            slave_data.available = True

            # Clear pending request
            del self._pending_requests[f"{slave_id}_coils"]

            _LOGGER.debug(
                "Slave %s: Updated %d coils",
                slave_id,
                len(slave_data.coils),
            )

            # Notify coordinator (throttled)
            self._update_coordinator_throttled()

        # Detect Read Holding Registers request (function 03) for monitored registers
        elif (
            frame.is_request
            and frame.function_code == 3
            and frame.start_address == REGISTER_START_ADDRESS
            and frame.register_count == REGISTER_MONITOR_COUNT
        ):
            self._pending_requests[f"{slave_id}_registers"] = {
                "timestamp": utcnow(),
                "slave_id": slave_id,
                "type": "registers",
                "start_address": frame.start_address,
            }

        # Handle Read Holding Registers response for monitored registers
        elif (
            frame.is_response
            and frame.function_code == 3
            and f"{slave_id}_registers" in self._pending_requests
            and frame.values
        ):
            # Ensure slave exists
            if slave_id not in self.discovered_slaves:
                _LOGGER.info("Discovered new slave via registers: %s", slave_id)
                self.discovered_slaves[slave_id] = SlaveData(
                    slave_id=slave_id,
                    temperature=None,
                    humidity=None,
                    last_seen=utcnow(),
                    available=False,
                )

            # Get start address from pending request
            start_addr = self._pending_requests[f"{slave_id}_registers"]["start_address"]

            # Update register data - convert unsigned to signed int16
            slave_data = self.discovered_slaves[slave_id]
            if slave_data.registers is None:
                slave_data.registers = {}

            for idx, value in enumerate(frame.values):
                register_addr = start_addr + idx
                # Convert unsigned 16-bit to signed int16
                if value > 32767:
                    signed_value = value - 65536
                else:
                    signed_value = value
                slave_data.registers[register_addr] = signed_value

            slave_data.last_seen = utcnow()
            slave_data.available = True

            # Clear pending request
            del self._pending_requests[f"{slave_id}_registers"]

            _LOGGER.debug(
                "Slave %s: Updated %d registers starting at %d",
                slave_id,
                len(frame.values),
                start_addr,
            )

            # Notify coordinator (throttled)
            self._update_coordinator_throttled()

        # Detect Read Holding Registers request (function 03) for second monitored register range
        elif (
            frame.is_request
            and frame.function_code == 3
            and frame.start_address == REGISTER_START_ADDRESS_2
            and frame.register_count == REGISTER_MONITOR_COUNT_2
        ):
            self._pending_requests[f"{slave_id}_registers2"] = {
                "timestamp": utcnow(),
                "slave_id": slave_id,
                "type": "registers2",
                "start_address": frame.start_address,
            }

        # Handle Read Holding Registers response for second monitored register range
        elif (
            frame.is_response
            and frame.function_code == 3
            and f"{slave_id}_registers2" in self._pending_requests
            and frame.values
        ):
            # Ensure slave exists
            if slave_id not in self.discovered_slaves:
                _LOGGER.info("Discovered new slave via registers2: %s", slave_id)
                self.discovered_slaves[slave_id] = SlaveData(
                    slave_id=slave_id,
                    temperature=None,
                    humidity=None,
                    last_seen=utcnow(),
                    available=False,
                )

            # Get start address from pending request
            start_addr = self._pending_requests[f"{slave_id}_registers2"]["start_address"]

            # Update register data - convert unsigned to signed int16
            slave_data = self.discovered_slaves[slave_id]
            if slave_data.registers is None:
                slave_data.registers = {}

            for idx, value in enumerate(frame.values):
                register_addr = start_addr + idx
                # Convert unsigned 16-bit to signed int16
                if value > 32767:
                    signed_value = value - 65536
                else:
                    signed_value = value
                slave_data.registers[register_addr] = signed_value

            slave_data.last_seen = utcnow()
            slave_data.available = True

            # Clear pending request
            del self._pending_requests[f"{slave_id}_registers2"]

            _LOGGER.debug(
                "Slave %s: Updated %d registers (range 2) starting at %d",
                slave_id,
                len(frame.values),
                start_addr,
            )

            # Notify coordinator (throttled)
            self._update_coordinator_throttled()

        # Detect Read Holding Registers request (function 03) for third monitored register range
        elif (
            frame.is_request
            and frame.function_code == 3
            and frame.start_address == REGISTER_START_ADDRESS_3
            and frame.register_count == REGISTER_MONITOR_COUNT_3
        ):
            self._pending_requests[f"{slave_id}_registers3"] = {
                "timestamp": utcnow(),
                "slave_id": slave_id,
                "type": "registers3",
                "start_address": frame.start_address,
            }

        # Handle Read Holding Registers response for third monitored register range
        elif (
            frame.is_response
            and frame.function_code == 3
            and f"{slave_id}_registers3" in self._pending_requests
            and frame.values
        ):
            # Ensure slave exists
            if slave_id not in self.discovered_slaves:
                _LOGGER.info("Discovered new slave via registers3: %s", slave_id)
                self.discovered_slaves[slave_id] = SlaveData(
                    slave_id=slave_id,
                    temperature=None,
                    humidity=None,
                    last_seen=utcnow(),
                    available=False,
                )

            # Get start address from pending request
            start_addr = self._pending_requests[f"{slave_id}_registers3"]["start_address"]

            # Update register data - convert unsigned to signed int16
            slave_data = self.discovered_slaves[slave_id]
            if slave_data.registers is None:
                slave_data.registers = {}

            for idx, value in enumerate(frame.values):
                register_addr = start_addr + idx
                # Convert unsigned 16-bit to signed int16
                if value > 32767:
                    signed_value = value - 65536
                else:
                    signed_value = value
                slave_data.registers[register_addr] = signed_value

            slave_data.last_seen = utcnow()
            slave_data.available = True

            # Clear pending request
            del self._pending_requests[f"{slave_id}_registers3"]

            _LOGGER.debug(
                "Slave %s: Updated %d registers (range 3) starting at %d",
                slave_id,
                len(frame.values),
                start_addr,
            )

            # Notify coordinator (throttled)
            self._update_coordinator_throttled()

        # Detect discovery: request to register 0x83 with 4 registers
        elif (
            frame.is_request
            and frame.start_address == TEMP_HUMIDITY_REGISTER
            and frame.register_count == REGISTER_COUNT
        ):
            self._pending_requests[slave_id] = {
                "timestamp": utcnow(),
                "slave_id": slave_id,
            }

            # Auto-discover new slave
            if slave_id not in self.discovered_slaves:
                _LOGGER.info("Discovered new slave: %s", slave_id)
                self.discovered_slaves[slave_id] = SlaveData(
                    slave_id=slave_id,
                    temperature=None,
                    humidity=None,
                    last_seen=utcnow(),
                    available=False,
                )
                # Trigger entity creation (throttled)
                self._update_coordinator_throttled()

        # Handle response with temperature/humidity data
        elif (
            frame.is_response
            and slave_id in self._pending_requests
            and frame.values
            and len(frame.values) >= 4
        ):
            # Extract temperature (index 2) and humidity (index 3)
            temp_raw = frame.values[2]
            humidity_raw = frame.values[3]

            # Scale values (divide by 10)
            temperature = temp_raw / 10.0
            humidity = humidity_raw / 10.0

            # Update slave data
            slave_data = self.discovered_slaves[slave_id]
            slave_data.temperature = temperature
            slave_data.humidity = humidity
            slave_data.last_seen = utcnow()
            slave_data.available = True

            # Clear pending request
            del self._pending_requests[slave_id]

            _LOGGER.debug(
                "Slave %s: Temperature=%.1f°C, Humidity=%.1f%%",
                slave_id,
                temperature,
                humidity,
            )

            # Notify coordinator (throttled)
            self._update_coordinator_throttled()

    async def _availability_check_loop(self) -> None:
        """Periodically check slave availability."""
        while True:
            try:
                await asyncio.sleep(15)  # Check every 15 s
                self._check_slave_availability()
            except asyncio.CancelledError:
                break
            except Exception as ex:
                _LOGGER.error("Error in availability check loop: %s", ex)

    def _check_slave_availability(self) -> None:
        """Mark slaves unavailable if no data received recently."""
        now = utcnow()
        updated = False

        for slave_data in self.discovered_slaves.values():
            if (now - slave_data.last_seen) > AVAILABILITY_TIMEOUT:
                if slave_data.available:
                    slave_data.available = False
                    updated = True
                    _LOGGER.warning("Slave %s marked unavailable", slave_data.slave_id)

        if updated:
            self._update_coordinator_throttled()

    async def async_write_setpoint(
        self, slave_id: int, temperature: float
    ) -> None:
        """Write temperature setpoint to slave using RTU protocol over existing connection."""
        async with self._write_lock:
            # Ensure writer is available and not closed
            if not self._writer or self._writer.is_closing():
                raise HomeAssistantError(
                    f"No active connection to Modbus gateway at {self.host}:{self.port} - cannot write setpoint"
                )

            # Scale temperature value (multiply by 10)
            value = int(temperature * 10)

            # Ensure value fits in uint16
            if not 0 <= value <= 65535:
                raise HomeAssistantError(
                    f"Setpoint value {value} out of valid range (0-65535)"
                )

            _LOGGER.info(
                "Writing setpoint via RTU - slave_id=%s, temp=%.1f°C, scaled_value=%d, register=%s",
                slave_id,
                temperature,
                value,
                SETPOINT_REGISTER,
            )

            try:
                # Build Modbus RTU Write Single Register frame
                frame = self._decoder.build_write_register_frame(
                    slave_id=slave_id,
                    register=SETPOINT_REGISTER,
                    value=value,
                )

                _LOGGER.debug(
                    "Sending RTU frame: %s (length=%d)",
                    frame.hex(" "),
                    len(frame),
                )

                # Send frame via existing TCP connection
                self._writer.write(frame)
                await self._writer.drain()

                _LOGGER.info(
                    "Successfully sent setpoint %.1f°C (value=%d) to slave %s register %s",
                    temperature,
                    value,
                    slave_id,
                    SETPOINT_REGISTER,
                )

                # Note: We don't wait for response here as the passive monitoring
                # loop will receive and process it. The Write Single Register
                # response echoes the request if successful, or returns an error code.

            except OSError as ex:
                _LOGGER.exception(
                    "Connection error writing setpoint to slave %s: %s",
                    slave_id,
                    ex,
                )
                raise HomeAssistantError(
                    f"Connection error writing setpoint to slave {slave_id}"
                ) from ex
            except Exception as ex:
                _LOGGER.exception(
                    "Unexpected error writing setpoint to slave %s: %s",
                    slave_id,
                    ex,
                )
                raise HomeAssistantError(
                    f"Unexpected error writing setpoint to slave {slave_id}"
                ) from ex

    async def async_close(self) -> None:
        """Close hub and cleanup resources."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        if self._availability_task:
            self._availability_task.cancel()
            try:
                await self._availability_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        _LOGGER.info("Modbus RTU Monitor hub closed")
