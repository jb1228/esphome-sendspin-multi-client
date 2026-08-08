import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_TYPE
from esphome.types import ConfigType

from .. import (
    CONF_SENDSPIN_MC_ID,
    SendspinMcHub,
    request_metadata_support,
    sendspin_mc_ns,
)

CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["sendspin_mc"]

SendspinMcTextSensor = sendspin_mc_ns.class_(
    "SendspinMcTextSensor",
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
    request_metadata_support(config[CONF_SENDSPIN_MC_ID])

    return config


CONFIG_SCHEMA = cv.All(
    text_sensor.text_sensor_schema().extend(
        {
            cv.GenerateID(): cv.declare_id(SendspinMcTextSensor),
            cv.GenerateID(CONF_SENDSPIN_MC_ID): cv.use_id(SendspinMcHub),
            cv.Required(CONF_TYPE): cv.enum(SENDSPIN_TEXT_METADATA_TYPES),
        }
    ),
    cv.only_on_esp32,
    _request_roles,
)


async def to_code(config: ConfigType) -> None:
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await cg.register_parented(var, config[CONF_SENDSPIN_MC_ID])
    await text_sensor.register_text_sensor(var, config)

    cg.add(var.set_metadata_type(config[CONF_TYPE]))
