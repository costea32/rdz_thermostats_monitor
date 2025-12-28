"""The Modbus RTU Monitor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .coordinator import ModbusRTUMonitorCoordinator
from .hub import ModbusRTUMonitorHub

type ModbusRTUMonitorConfigEntry = ConfigEntry[ModbusRTUMonitorCoordinator]

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: ModbusRTUMonitorConfigEntry
) -> bool:
    """Set up Modbus RTU Monitor from a config entry."""
    # Create hub
    hub = ModbusRTUMonitorHub(
        hass,
        entry,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
    )

    # Create coordinator
    coordinator = ModbusRTUMonitorCoordinator(hass, entry, hub)
    hub.coordinator = coordinator  # Link back to coordinator

    # Setup hub (connect and start monitoring)
    if not await hub.async_setup():
        return False

    # Store in runtime_data
    entry.runtime_data = coordinator

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ModbusRTUMonitorConfigEntry
) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Close hub
        await entry.runtime_data.hub.async_close()

    return unload_ok
