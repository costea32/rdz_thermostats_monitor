"""DataUpdateCoordinator for Modbus RTU Monitor."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SlaveData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .hub import ModbusRTUMonitorHub

_LOGGER = logging.getLogger(__name__)


class ModbusRTUMonitorCoordinator(DataUpdateCoordinator[dict[int, SlaveData]]):
    """Coordinator for Modbus RTU Monitor state updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        hub: ModbusRTUMonitorHub,
    ) -> None:
        """Initialize coordinator."""
        self.hub = hub

        # No update_interval - updates come from passive monitoring
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=None,  # Push-based updates
        )

    async def _async_update_data(self) -> dict[int, SlaveData]:
        """Not used - data comes from passive monitoring.

        This method won't be called due to update_interval=None.
        Updates happen via hub calling async_set_updated_data().
        """
        return self.hub.discovered_slaves
