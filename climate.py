"""Climate platform for Modbus RTU Monitor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ModbusRTUMonitorConfigEntry
from .const import DOMAIN, HEATING_STATUS_REGISTER, MANUFACTURER, MODEL, SETPOINT_REGISTER
from .coordinator import ModbusRTUMonitorCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ModbusRTUMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities from a config entry."""
    coordinator = entry.runtime_data

    # Track which slaves have climate entities
    added_slaves: set[int] = set()

    @callback
    def _async_add_climate_entities() -> None:
        """Add climate entities for newly discovered slaves."""
        if coordinator.data is None:
            return

        current_slaves = set(coordinator.data.keys())
        new_slaves = current_slaves - added_slaves

        if new_slaves:
            async_add_entities(
                ModbusRTUMonitorClimate(coordinator, slave_id)
                for slave_id in new_slaves
            )
            added_slaves.update(new_slaves)

    # Subscribe to coordinator updates
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_climate_entities)
    )

    # Add entities for already discovered slaves
    _async_add_climate_entities()


class ModbusRTUMonitorClimate(
    CoordinatorEntity[ModbusRTUMonitorCoordinator], ClimateEntity
):
    """Climate entity for Modbus RTU temperature monitor."""

    _attr_has_entity_name = True
    _attr_name = None  # Device name will be used
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]  # Always on, no off mode
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(
        self,
        coordinator: ModbusRTUMonitorCoordinator,
        slave_id: int,
    ) -> None:
        """Initialize climate entity."""
        super().__init__(coordinator)

        self._slave_id = slave_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{slave_id}_climate"
        )

        # Device info (groups climate + humidity sensor)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.config_entry.entry_id}_{slave_id}")},
            name=f"Modbus Slave {slave_id}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

        # Target temperature cache (synced from register 144 when available)
        self._attr_target_temperature = 20.0  # Default fallback

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._slave_id not in self.coordinator.data:
            return False
        return self.coordinator.data[self._slave_id].available

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature from passive monitoring."""
        if self._slave_id not in self.coordinator.data:
            return None
        return self.coordinator.data[self._slave_id].temperature

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature from device register or local cache."""
        if self._slave_id not in self.coordinator.data:
            return self._attr_target_temperature

        slave_data = self.coordinator.data[self._slave_id]

        # Try to read from register 144 (setpoint register)
        if slave_data.registers and SETPOINT_REGISTER in slave_data.registers:
            # Scale register value (divide by 10) to get temperature in °C
            setpoint_raw = slave_data.registers[SETPOINT_REGISTER]
            # Update local cache to stay in sync with device
            self._attr_target_temperature = setpoint_raw / 10.0
            return self._attr_target_temperature

        # Fall back to local cache if register not yet read
        return self._attr_target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        # Always HEAT mode (no on/off control as per requirements)
        return HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action based on heating status register."""
        if self._slave_id not in self.coordinator.data:
            return None

        slave_data = self.coordinator.data[self._slave_id]

        # Read heating status from register 213
        if slave_data.registers and HEATING_STATUS_REGISTER in slave_data.registers:
            heating_status = slave_data.registers[HEATING_STATUS_REGISTER]
            # Return HEATING if register value is 1, otherwise IDLE
            return HVACAction.HEATING if heating_status == 1 else HVACAction.IDLE

        # If register not available, return None (unknown state)
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature and write to device."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        # Update local target temperature
        self._attr_target_temperature = temperature

        # Write to device via hub
        try:
            await self.coordinator.hub.async_write_setpoint(
                self._slave_id,
                temperature,
            )
        except Exception as ex:
            raise HomeAssistantError(
                f"Failed to set temperature for slave {self._slave_id}"
            ) from ex

        # Update state
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        # No on/off control - only HEAT mode supported
        if hvac_mode != HVACMode.HEAT:
            raise HomeAssistantError(
                f"HVAC mode {hvac_mode} not supported. Only HEAT mode is available."
            )
