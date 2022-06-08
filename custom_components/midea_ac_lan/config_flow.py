import logging
from .const import DOMAIN, CONF_KEY, CONF_MAKE_SWITCH, OPEN_MIDEA_APP_ACCOUNT, OPEN_MIDEA_APP_PASSWORD
from homeassistant import config_entries
from homeassistant.const import (
    CONF_DEVICE, CONF_TOKEN, CONF_DEVICE_ID,
    CONF_HOST, CONF_PROTOCOL, CONF_PORT, CONF_MODEL
)
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from .midea.discover import discover
from .midea.mideacloud import MideaCloud
from .state_manager import DeviceManager
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

ADD_WAY = {"auto": "Auto", "manually": "Manually"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    available_device = []
    devices = {}
    cur_device_id = None

    def _already_configured(self, device_id):
        for entry in self._async_current_entries():
            if device_id == entry.data[CONF_DEVICE_ID]:
                return True
        return False

    async def async_step_user(self, user_input=None, error=None):
        if user_input is not None:
            if user_input["action"] == "auto":
                return await self.async_step_discover()
            else:
                return await self.async_step_manually()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("action", default="auto"): vol.In(ADD_WAY)
            }),
            errors={"base": error} if error else None
        )

    async def async_step_discover(self, user_input=None, error=None):
        if user_input is not None:
            self.devices = discover()
            self.available_device = []
            for device_id, device in self.devices.items():
                if not self._already_configured(device_id):
                    self.available_device.append(device_id)
            if len(self.available_device) > 0:
                return await self.async_step_auto()
            else:
                return await self.async_step_user(error="no_devices")
        return self.async_show_form(
            step_id="discover",
            errors={"base": error} if error else None
        )

    async def async_step_auto(self, user_input=None, error=None):
        if user_input is not None:
            device_id = user_input[CONF_DEVICE]
            device = self.devices.get(device_id)
            _LOGGER.debug(f"Now config device {device}")
            if device.get("protocol") == 3:
                session = async_create_clientsession(self.hass)
                cloud = MideaCloud(session, OPEN_MIDEA_APP_ACCOUNT, OPEN_MIDEA_APP_PASSWORD, "oc")
                if await cloud.login():
                    for byte_order_big in [True, False]:
                        token, key = await cloud.get_token(user_input[CONF_DEVICE], byte_order_big=byte_order_big)
                        if token and key:
                            dm = DeviceManager(device_id, device.get("ip"), device.get("port"),
                                               token, key, 3, "")
                            _LOGGER.debug(f"Successful to take token and key, token = {token}, key = {key}, "
                                          f"byte_order_big = {byte_order_big}")
                            if dm.open(False):
                                return self.async_create_entry(
                                    title=f"{device_id}",
                                    data={
                                        CONF_DEVICE_ID: device_id,
                                        CONF_PROTOCOL: 3,
                                        CONF_HOST: device.get("ip"),
                                        CONF_PORT: device.get("port"),
                                        CONF_MODEL: device.get("model"),
                                        CONF_MAKE_SWITCH: user_input[CONF_MAKE_SWITCH],
                                        CONF_TOKEN: token,
                                        CONF_KEY: key,
                                    })

                return await self.async_step_auto(error="cant_get_token")
            else:
                return self.async_create_entry(
                    title=f"{device_id}",
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_PROTOCOL: 2,
                        CONF_HOST: device.get("ip"),
                        CONF_PORT: device.get("port"),
                        CONF_MODEL: device.get("model"),
                        CONF_MAKE_SWITCH: user_input[CONF_MAKE_SWITCH]
                    })
        return self.async_show_form(
            step_id="auto",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE, default=sorted(self.available_device)[0]):
                    vol.In(self.available_device),
                vol.Required(CONF_MAKE_SWITCH, default=True): bool,
            }),
            errors={"base": error} if error else None
        )

    async def async_step_manually(self, user_input=None, error=None):
        if user_input is not None:
            dm = DeviceManager(user_input[CONF_DEVICE_ID], user_input[CONF_HOST], user_input[CONF_PORT],
                               user_input[CONF_TOKEN], user_input[CONF_KEY], user_input[CONF_PROTOCOL],
                               user_input[CONF_MODEL])
            if dm.open(False):
                dm.close()
                return self.async_create_entry(
                    title=f"{user_input[CONF_DEVICE_ID]}",
                    data={
                        CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                        CONF_PROTOCOL: user_input[CONF_PROTOCOL],
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_MODEL: user_input[CONF_MODEL],
                        CONF_MAKE_SWITCH: user_input[CONF_MAKE_SWITCH],
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_KEY: user_input[CONF_KEY],
                    })
            else:
                return await self.async_step_user(error="config_incorrect")

        return self.async_show_form(
            step_id="manually",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): int,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=6444): int,
                vol.Required(CONF_PROTOCOL, default=3): vol.In({2: "V2", 3: "V3"}),
                vol.Required(CONF_MODEL, default="Unknown"): str,
                vol.Optional(CONF_TOKEN): str,
                vol.Optional(CONF_KEY): str,
                vol.Optional(CONF_MAKE_SWITCH, default=True): bool,
            }),
            errors={"base": error} if error else None
        )
    """
    async def async_step_protocol(self, user_input=None, error=None):
        if user_input is not None:
            device = self.devices.get(self.cur_device_id)
            user_input[CONF_DEVICE_ID] = self.cur_device_id
            user_input[CONF_MAKE_SWITCH] = device[CONF_MAKE_SWITCH]
            return self.async_create_entry(
                title=f"{self.cur_device_id}",
                data={
                    CONF_DEVICE_ID: self.cur_device_id,
                    CONF_PROTOCOL: 3,
                    CONF_HOST: device.get("ip"),
                    CONF_PORT: device.get("port"),
                    CONF_MODEL: device.get("model"),
                    CONF_MAKE_SWITCH: device[CONF_MAKE_SWITCH],
                    CONF_TOKEN: user_input[CONF_TOKEN],
                    CONF_KEY: user_input[CONF_KEY],
                })
        return self.async_show_form(
            step_id="protocol",
            data_schema=vol.Schema({
                vol.Required(CONF_TOKEN): str,
                vol.Required(CONF_KEY): str
            }),
            errors={"base": error} if error else None
        )
    """
