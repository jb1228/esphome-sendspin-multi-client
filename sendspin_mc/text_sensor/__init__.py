import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_TYPE
from esphome.types import ConfigType

from .. import (
    CONF_SENDSPIN_MC_ID,
    SendspinMcHub,
    request_metadata_support,
    request_pairing_code_display_support,
    sendspin_mc_ns,
)

CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["sendspin_mc"]

CONF_PAIRING_CODE = "pairing_code"

SendspinMcTextSensor = sendspin_mc_ns.class_(
    "SendspinMcTextSensor",
    text_sensor.TextSensor,
    cg.Component,
)
SendspinMcPairingCodeTextSensor = sendspin_mc_ns.class_(
    "SendspinMcPairingCodeTextSensor",
    text_sensor.TextSensor,
    cg.Component,
)

SendspinMcTextMetadataTypes = sendspin_mc_ns.enum(
    "SendspinMcTextMetadataTypes", is_class=True
)
SENDSPIN_TEXT_METADATA_TYPES = {
    "title": SendspinMcTextMetadataTypes.TITLE,
    "artist": SendspinMcTextMetadataTypes.ARTIST,
    "album": SendspinMcTextMetadataTypes.ALBUM,
    "album_artist": SendspinMcTextMetadataTypes.ALBUM_ARTIST,
}


def _request_roles(config: ConfigType) -> ConfigType:
    """Request the necessary Sendspin roles for the text sensor."""
    if config[CONF_TYPE] == CONF_PAIRING_CODE:
        # A display surface for the dynamic code, so advertise dynamic_pairing_code.
        request_pairing_code_display_support(config[CONF_SENDSPIN_MC_ID])
    else:
        request_metadata_support(config[CONF_SENDSPIN_MC_ID])

    return config


_HUB_ID_SCHEMA = cv.Schema({cv.GenerateID(CONF_SENDSPIN_MC_ID): cv.use_id(SendspinMcHub)})
_METADATA_SCHEMA = text_sensor.text_sensor_schema(SendspinMcTextSensor).extend(
    _HUB_ID_SCHEMA
)

CONFIG_SCHEMA = cv.All(
    cv.typed_schema(
        {
            **dict.fromkeys(SENDSPIN_TEXT_METADATA_TYPES, _METADATA_SCHEMA),
            CONF_PAIRING_CODE: text_sensor.text_sensor_schema(
                SendspinMcPairingCodeTextSensor
            ).extend(_HUB_ID_SCHEMA),
        },
        key=CONF_TYPE,
    ),
    cv.only_on_esp32,
    _request_roles,
)


async def to_code(config: ConfigType) -> None:
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await cg.register_parented(var, config[CONF_SENDSPIN_MC_ID])
    await text_sensor.register_text_sensor(var, config)

    if (
        metadata_type := SENDSPIN_TEXT_METADATA_TYPES.get(config[CONF_TYPE])
    ) is not None:
        cg.add(var.set_metadata_type(metadata_type))
