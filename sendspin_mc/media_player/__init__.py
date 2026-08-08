import esphome.codegen as cg
from esphome.components import media_player
from esphome.components.const import CONF_VOLUME_INCREMENT
import esphome.config_validation as cv
from esphome.const import CONF_ID
from esphome.types import ConfigType

from .. import (
    CONF_SENDSPIN_MC_ID,
    SendspinMcHub,
    request_controller_support,
    sendspin_mc_ns,
)

CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["sendspin_mc"]

SendspinMcMediaPlayer = sendspin_mc_ns.class_(
    "SendspinMcMediaPlayer",
    media_player.MediaPlayer,
    cg.Component,
)


def _request_roles(config: ConfigType) -> ConfigType:
    """Request the necessary Sendspin roles for the media player."""
    request_controller_support(config[CONF_SENDSPIN_MC_ID])

    return config


CONFIG_SCHEMA = cv.All(
    media_player.media_player_schema(SendspinMcMediaPlayer).extend(
        {
            cv.GenerateID(CONF_SENDSPIN_MC_ID): cv.use_id(SendspinMcHub),
            cv.Optional(CONF_VOLUME_INCREMENT, default=0.05): cv.percentage,
        }
    ),
    cv.only_on_esp32,
    _request_roles,
)


async def to_code(config: ConfigType) -> None:
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await cg.register_parented(var, config[CONF_SENDSPIN_MC_ID])
    await media_player.register_media_player(var, config)

    cg.add(var.set_volume_increment(config[CONF_VOLUME_INCREMENT]))
