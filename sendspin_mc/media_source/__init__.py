from esphome import automation
import esphome.codegen as cg
from esphome.components import media_source, psram
import esphome.config_validation as cv
from esphome.const import (
    CONF_BITS_PER_SAMPLE,
    CONF_BUFFER_SIZE,
    CONF_CHANNELS,
    CONF_ID,
    CONF_SAMPLE_RATE,
    CONF_TASK_STACK_IN_PSRAM,
)
from esphome.core import ID
from esphome.cpp_generator import MockObj, TemplateArgsType
from esphome.types import ConfigType

from .. import (
    CONF_DECODE_MEMORY,
    CONF_FIXED_DELAY,
    CONF_INITIAL_STATIC_DELAY,
    CONF_SENDSPIN_MC_ID,
    MEMORY_LOCATIONS,
    SendspinMcHub,
    register_player_config,
    request_controller_support,
    sendspin_mc_ns,
)

AUTO_LOAD = ["audio"]
CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["sendspin_mc"]

CONF_STATIC_DELAY_ADJUSTABLE = "static_delay_adjustable"

SendspinMcMediaSource = sendspin_mc_ns.class_(
    "SendspinMcMediaSource",
    cg.Component,
    media_source.MediaSource,
)

EnableStaticDelayAdjustmentAction = sendspin_mc_ns.class_(
    "EnableStaticDelayAdjustmentAction",
    automation.Action,
    cg.Parented.template(SendspinMcMediaSource),
)

DisableStaticDelayAdjustmentAction = sendspin_mc_ns.class_(
    "DisableStaticDelayAdjustmentAction",
    automation.Action,
    cg.Parented.template(SendspinMcMediaSource),
)


def _register(config: ConfigType) -> ConfigType:
    hub_id = config[CONF_SENDSPIN_MC_ID]
    request_controller_support(hub_id)
    register_player_config(
        hub_id,
        {
            CONF_SAMPLE_RATE: config[CONF_SAMPLE_RATE],
            CONF_BITS_PER_SAMPLE: config[CONF_BITS_PER_SAMPLE],
            CONF_CHANNELS: config[CONF_CHANNELS],
            CONF_BUFFER_SIZE: config[CONF_BUFFER_SIZE],
            CONF_INITIAL_STATIC_DELAY: config[CONF_INITIAL_STATIC_DELAY],
            CONF_FIXED_DELAY: config[CONF_FIXED_DELAY],
            CONF_TASK_STACK_IN_PSRAM: config.get(CONF_TASK_STACK_IN_PSRAM, False),
            CONF_DECODE_MEMORY: config.get(CONF_DECODE_MEMORY),
        },
    )
    return config


CONFIG_SCHEMA = cv.All(
    media_source.media_source_schema(
        SendspinMcMediaSource,
    ).extend(
        {
            cv.GenerateID(CONF_SENDSPIN_MC_ID): cv.use_id(SendspinMcHub),
            cv.Optional(CONF_TASK_STACK_IN_PSRAM): psram.validate_task_stack_in_psram,
            cv.Optional(CONF_BUFFER_SIZE, default=1000000): cv.int_range(min=25000),
            cv.Optional(CONF_INITIAL_STATIC_DELAY, default="0ms"): cv.All(
                cv.positive_time_period_milliseconds,
                cv.Range(max=cv.TimePeriod(milliseconds=5000)),
            ),
            cv.Optional(CONF_STATIC_DELAY_ADJUSTABLE, default=False): cv.boolean,
            cv.Optional(CONF_FIXED_DELAY, default="0us"): cv.All(
                cv.positive_time_period_microseconds,
                cv.Range(max=cv.TimePeriod(microseconds=10000)),
            ),
            cv.Optional(CONF_SAMPLE_RATE, default=48000): cv.int_range(
                min=16000, max=96000
            ),
            cv.Optional(CONF_BITS_PER_SAMPLE, default=16): cv.one_of(16, int=True),
            cv.Optional(CONF_CHANNELS, default=2): cv.int_range(min=1, max=2),
            cv.Optional(CONF_DECODE_MEMORY): cv.one_of(*MEMORY_LOCATIONS, lower=True),
        }
    ),
    cv.only_on_esp32,
    _register,
)


async def to_code(config: ConfigType) -> None:
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await media_source.register_media_source(var, config)

    sendspin_hub = await cg.get_variable(config[CONF_SENDSPIN_MC_ID])
    await cg.register_parented(var, sendspin_hub)

    cg.add(sendspin_hub.set_listener(var))
    cg.add(var.set_static_delay_adjustable(config[CONF_STATIC_DELAY_ADJUSTABLE]))


SENDSPIN_MC_MEDIA_SOURCE_ACTION_SCHEMA = automation.maybe_simple_id(
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(SendspinMcMediaSource),
        }
    )
)


@automation.register_action(
    "sendspin_mc.media_source.enable_static_delay_adjustment",
    EnableStaticDelayAdjustmentAction,
    SENDSPIN_MC_MEDIA_SOURCE_ACTION_SCHEMA,
    synchronous=True,
)
@automation.register_action(
    "sendspin_mc.media_source.disable_static_delay_adjustment",
    DisableStaticDelayAdjustmentAction,
    SENDSPIN_MC_MEDIA_SOURCE_ACTION_SCHEMA,
    synchronous=True,
)
async def sendspin_mc_static_delay_adjustment_to_code(
    config: ConfigType,
    action_id: ID,
    template_arg: cg.TemplateArguments,
    args: TemplateArgsType,
) -> MockObj:
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var
