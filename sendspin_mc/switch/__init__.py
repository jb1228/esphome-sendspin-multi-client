import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch
from esphome.const import ENTITY_CATEGORY_CONFIG
from esphome.types import ConfigType

from .. import CONF_SENDSPIN_MC_ID, SendspinMcHub, sendspin_mc_ns

CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["sendspin_mc"]

SendspinMcSwitch = sendspin_mc_ns.class_(
    "SendspinMcSwitch", switch.Switch, cg.Component
)

CONFIG_SCHEMA = cv.All(
    switch.switch_schema(
        SendspinMcSwitch,
        block_inverted=True,
        default_restore_mode="RESTORE_DEFAULT_ON",
        entity_category=ENTITY_CATEGORY_CONFIG,
    )
    .extend({cv.GenerateID(CONF_SENDSPIN_MC_ID): cv.use_id(SendspinMcHub)})
    .extend(cv.COMPONENT_SCHEMA),
    cv.only_on_esp32,
)


async def to_code(config: ConfigType) -> None:
    var = await switch.new_switch(config)
    await cg.register_component(var, config)
    await cg.register_parented(var, config[CONF_SENDSPIN_MC_ID])
