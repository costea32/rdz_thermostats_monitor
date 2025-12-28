"""Sensor platform for Modbus RTU Monitor."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ModbusRTUMonitorConfigEntry
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    REGISTER_MONITOR_COUNT,
    REGISTER_MONITOR_COUNT_2,
    REGISTER_MONITOR_COUNT_3,
    REGISTER_START_ADDRESS,
    REGISTER_START_ADDRESS_2,
    REGISTER_START_ADDRESS_3,
)
from .coordinator import ModbusRTUMonitorCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ModbusRTUMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator = entry.runtime_data

    # Track which slaves have sensor entities
    added_slaves: set[int] = set()
    added_slaves_registers: set[int] = set()
    added_slaves_registers2: set[int] = set()
    added_slaves_registers3: set[int] = set()

    @callback
    def _async_add_sensor_entities() -> None:
        """Add sensor entities for newly discovered slaves."""
        if coordinator.data is None:
            return

        entities = []

        # Add humidity sensors for new slaves
        current_slaves = set(coordinator.data.keys())
        new_slaves = current_slaves - added_slaves

        if new_slaves:
            for slave_id in new_slaves:
                entities.append(
                    ModbusRTUMonitorHumiditySensor(coordinator, slave_id)
                )
            added_slaves.update(new_slaves)

        # Add register sensors for slaves with register data (range 1: 165-184)
        current_slaves_registers = {
            slave_id
            for slave_id, slave_data in coordinator.data.items()
            if slave_data.registers is not None
            and any(
                REGISTER_START_ADDRESS <= addr < REGISTER_START_ADDRESS + REGISTER_MONITOR_COUNT
                for addr in slave_data.registers
            )
        }
        new_slaves_registers = current_slaves_registers - added_slaves_registers

        if new_slaves_registers:
            for slave_id in new_slaves_registers:
                # Create sensors for each monitored register (range 1)
                for reg_offset in range(REGISTER_MONITOR_COUNT):
                    register_addr = REGISTER_START_ADDRESS + reg_offset
                    entities.append(
                        ModbusRTUMonitorRegisterSensor(
                            coordinator, slave_id, register_addr
                        )
                    )
            added_slaves_registers.update(new_slaves_registers)

        # Add register sensors for slaves with register data (range 2: 210-217)
        current_slaves_registers2 = {
            slave_id
            for slave_id, slave_data in coordinator.data.items()
            if slave_data.registers is not None
            and any(
                REGISTER_START_ADDRESS_2 <= addr < REGISTER_START_ADDRESS_2 + REGISTER_MONITOR_COUNT_2
                for addr in slave_data.registers
            )
        }
        new_slaves_registers2 = current_slaves_registers2 - added_slaves_registers2

        if new_slaves_registers2:
            for slave_id in new_slaves_registers2:
                # Create sensors for each monitored register (range 2)
                for reg_offset in range(REGISTER_MONITOR_COUNT_2):
                    register_addr = REGISTER_START_ADDRESS_2 + reg_offset
                    entities.append(
                        ModbusRTUMonitorRegisterSensor(
                            coordinator, slave_id, register_addr
                        )
                    )
            added_slaves_registers2.update(new_slaves_registers2)

        # Add register sensors for slaves with register data (range 3: 140-147)
        current_slaves_registers3 = {
            slave_id
            for slave_id, slave_data in coordinator.data.items()
            if slave_data.registers is not None
            and any(
                REGISTER_START_ADDRESS_3 <= addr < REGISTER_START_ADDRESS_3 + REGISTER_MONITOR_COUNT_3
                for addr in slave_data.registers
            )
        }
        new_slaves_registers3 = current_slaves_registers3 - added_slaves_registers3

        if new_slaves_registers3:
            for slave_id in new_slaves_registers3:
                # Create sensors for each monitored register (range 3)
                for reg_offset in range(REGISTER_MONITOR_COUNT_3):
                    register_addr = REGISTER_START_ADDRESS_3 + reg_offset
                    entities.append(
                        ModbusRTUMonitorRegisterSensor(
                            coordinator, slave_id, register_addr
                        )
                    )
            added_slaves_registers3.update(new_slaves_registers3)

        if entities:
            async_add_entities(entities)

    # Subscribe to coordinator updates
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_sensor_entities)
    )

    # Add entities for already discovered slaves
    _async_add_sensor_entities()


class ModbusRTUMonitorHumiditySensor(
    CoordinatorEntity[ModbusRTUMonitorCoordinator],
    SensorEntity,
):
    """Humidity sensor entity for Modbus RTU monitor."""

    _attr_has_entity_name = True
    _attr_translation_key = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ModbusRTUMonitorCoordinator,
        slave_id: int,
    ) -> None:
        """Initialize humidity sensor."""
        super().__init__(coordinator)

        self._slave_id = slave_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{slave_id}_humidity"
        )

        # Same device as climate entity
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.config_entry.entry_id}_{slave_id}")},
            name=f"Modbus Slave {slave_id}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._slave_id not in self.coordinator.data:
            return False
        return self.coordinator.data[self._slave_id].available

    @property
    def native_value(self) -> float | None:
        """Return humidity value from passive monitoring."""
        if self._slave_id not in self.coordinator.data:
            return None
        return self.coordinator.data[self._slave_id].humidity


class ModbusRTUMonitorRegisterSensor(
    CoordinatorEntity[ModbusRTUMonitorCoordinator],
    SensorEntity,
):
    """Register sensor entity for Modbus RTU monitor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ModbusRTUMonitorCoordinator,
        slave_id: int,
        register_addr: int,
    ) -> None:
        """Initialize register sensor."""
        super().__init__(coordinator)

        self._slave_id = slave_id
        self._register_addr = register_addr

        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{slave_id}_register{register_addr}"
        )
        self._attr_name = f"Register{register_addr}"

        # Same device as climate and humidity entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.config_entry.entry_id}_{slave_id}")},
            name=f"Modbus Slave {slave_id}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._slave_id not in self.coordinator.data:
            return False
        slave_data = self.coordinator.data[self._slave_id]
        if not slave_data.available or slave_data.registers is None:
            return False
        return self._register_addr in slave_data.registers

    @property
    def native_value(self) -> int | None:
        """Return register value (signed int16)."""
        if self._slave_id not in self.coordinator.data:
            return None
        slave_data = self.coordinator.data[self._slave_id]
        if slave_data.registers is None:
            return None
        return slave_data.registers.get(self._register_addr)

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Return additional state attributes."""
        return {"register_address": self._register_addr}
