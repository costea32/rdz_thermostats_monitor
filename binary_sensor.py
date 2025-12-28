"""Binary sensor platform for Modbus RTU Monitor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ModbusRTUMonitorConfigEntry
from .const import COIL_COUNT, DOMAIN, MANUFACTURER, MODEL
from .coordinator import ModbusRTUMonitorCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ModbusRTUMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    coordinator = entry.runtime_data

    # Track which slaves have binary sensor entities
    added_slaves: set[int] = set()

    @callback
    def _async_add_binary_sensor_entities() -> None:
        """Add binary sensor entities for newly discovered slaves with coil data."""
        if coordinator.data is None:
            return

        current_slaves = {
            slave_id
            for slave_id, slave_data in coordinator.data.items()
            if slave_data.coils is not None
        }
        new_slaves = current_slaves - added_slaves

        if new_slaves:
            entities = []
            for slave_id in new_slaves:
                # Create 40 binary sensors (coil1-40) for each slave
                for coil_idx in range(COIL_COUNT):
                    entities.append(
                        ModbusRTUMonitorCoilSensor(
                            coordinator, slave_id, coil_idx + 1
                        )
                    )
            async_add_entities(entities)
            added_slaves.update(new_slaves)

    # Subscribe to coordinator updates
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_binary_sensor_entities)
    )

    # Add entities for already discovered slaves with coil data
    _async_add_binary_sensor_entities()


class ModbusRTUMonitorCoilSensor(
    CoordinatorEntity[ModbusRTUMonitorCoordinator], BinarySensorEntity
):
    """Binary sensor entity for Modbus RTU coil state."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ModbusRTUMonitorCoordinator,
        slave_id: int,
        coil_number: int,
    ) -> None:
        """Initialize binary sensor entity."""
        super().__init__(coordinator)

        self._slave_id = slave_id
        self._coil_number = coil_number
        self._coil_idx = coil_number - 1  # Convert to 0-based index

        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{slave_id}_coil{coil_number}"
        )
        self._attr_name = f"Coil{coil_number}"

        # Device info (groups with climate and humidity sensor)
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
        if not slave_data.available or slave_data.coils is None:
            return False
        return self._coil_idx < len(slave_data.coils)

    @property
    def is_on(self) -> bool | None:
        """Return true if the coil is on."""
        if self._slave_id not in self.coordinator.data:
            return None
        slave_data = self.coordinator.data[self._slave_id]
        if slave_data.coils is None or self._coil_idx >= len(slave_data.coils):
            return None
        return slave_data.coils[self._coil_idx]

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Return additional state attributes."""
        return {"coil_number": self._coil_number}