import logging

import esphome.codegen as cg
from esphome.components import switch
from esphome.components.const import CONF_ENABLED
from esphome.components.switch import DOMAIN as SWITCH_DOMAIN
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_PLATFORM, CONF_TYPE, ENTITY_CATEGORY_CONFIG
import esphome.final_validate as fv
from esphome.types import ConfigType

from .. import (
    CONF_SENDSPIN_MC_ID,
    CONF_STATIC_PAIRING_CODE,
    CONF_UNPAIRED_ACCESS,
    DOMAIN,
    SendspinMcHub,
    _has_pairing_method,
    request_switch,
    sendspin_mc_ns,
)

_LOGGER = logging.getLogger(__name__)

CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["sendspin_mc"]

SendspinMcEnabledSwitch = sendspin_mc_ns.class_(
    "SendspinMcEnabledSwitch", switch.Switch, cg.Component
)
SendspinMcUnpairedAccessSwitch = sendspin_mc_ns.class_(
    "SendspinMcUnpairedAccessSwitch", switch.Switch, cg.Component
)


def _switch_schema(class_: cg.MockObjClass) -> cv.Schema:
    return (
        switch.switch_schema(
            class_,
            block_inverted=True,
            default_restore_mode="RESTORE_DEFAULT_ON",
            entity_category=ENTITY_CATEGORY_CONFIG,
        )
        .extend({cv.GenerateID(CONF_SENDSPIN_MC_ID): cv.use_id(SendspinMcHub)})
        .extend(cv.COMPONENT_SCHEMA)
    )


def _request_switch(config: ConfigType) -> ConfigType:
    """Tell the hub to wait for this switch before the client's first start."""
    request_switch(config[CONF_SENDSPIN_MC_ID], config[CONF_TYPE])
    return config


CONFIG_SCHEMA = cv.All(
    cv.typed_schema(
        {
            CONF_ENABLED: _switch_schema(SendspinMcEnabledSwitch),
            CONF_UNPAIRED_ACCESS: _switch_schema(SendspinMcUnpairedAccessSwitch),
        },
        key=CONF_TYPE,
    ),
    cv.only_on_esp32,
    _request_switch,
)


def _final_validate(config: ConfigType) -> ConfigType:
    full_config = fv.full_config.get()
    switch_type = config[CONF_TYPE]
    same_type = [
        conf
        for conf in full_config.get(SWITCH_DOMAIN, [])
        if conf.get(CONF_PLATFORM) == DOMAIN
        and conf.get(CONF_TYPE) == switch_type
        and conf[CONF_SENDSPIN_MC_ID] == config[CONF_SENDSPIN_MC_ID]
    ]
    # Two switches of one type would each drive the same hub setting.
    if len(same_type) > 1:
        raise cv.Invalid(f"Only one sendspin_mc '{switch_type}' switch is allowed per hub")
    if switch_type != CONF_UNPAIRED_ACCESS:
        return config
    hub_config = next(
        hub
        for hub in full_config[DOMAIN]
        if hub[CONF_ID] == config[CONF_SENDSPIN_MC_ID]
    )
    if CONF_UNPAIRED_ACCESS in hub_config:
        raise cv.Invalid(
            f"'{DOMAIN}: {CONF_UNPAIRED_ACCESS}' cannot be set together with an "
            f"{CONF_UNPAIRED_ACCESS} switch; set the switch's restore_mode instead"
        )
    if not _has_pairing_method(hub_config, full_config):
        _LOGGER.warning(
            "The %s switch has no pairing method (%s or a dynamic pairing code), so "
            "while it is off no new server can pair with this device",
            CONF_UNPAIRED_ACCESS,
            CONF_STATIC_PAIRING_CODE,
        )
    return config


FINAL_VALIDATE_SCHEMA = _final_validate


async def to_code(config: ConfigType) -> None:
    var = await switch.new_switch(config)
    await cg.register_component(var, config)
    await cg.register_parented(var, config[CONF_SENDSPIN_MC_ID])
    cg.add_define("USE_SENDSPIN_MC_SWITCH", True)
