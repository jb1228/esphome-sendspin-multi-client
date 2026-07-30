from dataclasses import dataclass

import esphome.codegen as cg
from esphome.components import network, psram, socket, wifi
import esphome.config_validation as cv
from esphome.const import (
    CONF_BITS_PER_SAMPLE,
    CONF_BUFFER_SIZE,
    CONF_CHANNELS,
    CONF_CLIENT_ID,
    CONF_ID,
    CONF_SAMPLE_RATE,
    CONF_TASK_STACK_IN_PSRAM,
)
from esphome.core import CORE, ID
from esphome.types import ConfigType

AUTO_LOAD = ["mdns"]
CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["network"]
DOMAIN = "sendspin_mc"
MULTI_CONF = True

CONF_CLIENT_NAME = "client_name"
CONF_CONTROL_PORT = "control_port"
CONF_DECODE_MEMORY = "decode_memory"
CONF_FIXED_DELAY = "fixed_delay"
CONF_INITIAL_STATIC_DELAY = "initial_static_delay"
CONF_SENDSPIN_MC_ID = "sendspin_mc_id"
CONF_SERVER_PORT = "server_port"

sendspin_library_ns = cg.global_ns.namespace("sendspin")

SendspinCodecFormat = sendspin_library_ns.enum("SendspinCodecFormat", is_class=True)
CODEC_FORMAT_FLAC = SendspinCodecFormat.enum("FLAC")
CODEC_FORMAT_OPUS = SendspinCodecFormat.enum("OPUS")
CODEC_FORMAT_PCM = SendspinCodecFormat.enum("PCM")

AudioSupportedFormatObject = sendspin_library_ns.struct("AudioSupportedFormatObject")
PlayerRoleConfig = sendspin_library_ns.struct("PlayerRoleConfig")

SendspinMemoryLocation = sendspin_library_ns.enum("MemoryLocation", is_class=True)

MEMORY_PSRAM = "psram"
MEMORY_INTERNAL = "internal"
MEMORY_LOCATIONS = [MEMORY_PSRAM, MEMORY_INTERNAL]
MEMORY_LOCATION_ENUM = {
    MEMORY_PSRAM: SendspinMemoryLocation.PREFER_EXTERNAL,
    MEMORY_INTERNAL: SendspinMemoryLocation.PREFER_INTERNAL,
}

sendspin_mc_ns = cg.esphome_ns.namespace("sendspin_mc")
SendspinMcHub = sendspin_mc_ns.class_("SendspinMcHub", cg.Component)


@dataclass
class SendspinMcConfiguration:
    controller_support: bool = False
    player_support: bool = False
    player_config: ConfigType | None = None


def _id_key(id_: ID) -> str:
    return id_.id


def _get_all_data() -> dict[str, SendspinMcConfiguration]:
    if DOMAIN not in CORE.data:
        CORE.data[DOMAIN] = {}
    return CORE.data[DOMAIN]


def _get_data(hub_id: ID) -> SendspinMcConfiguration:
    data = _get_all_data()
    key = _id_key(hub_id)
    if key not in data:
        data[key] = SendspinMcConfiguration()
    return data[key]


def request_controller_support(hub_id: ID) -> None:
    _get_data(hub_id).controller_support = True


def register_player_config(hub_id: ID, config: ConfigType) -> None:
    data = _get_data(hub_id)
    data.player_support = True
    if data.player_config is not None:
        raise cv.Invalid(
            f"Only one sendspin_mc media_source player configuration is supported for {hub_id.id}"
        )
    data.player_config = config


def _request_high_performance_networking(config: ConfigType) -> ConfigType:
    network.require_high_performance_networking()
    socket.consume_sockets(
        1, "sendspin_mc_websocket_server", socket.SocketType.TCP_LISTEN
    )(config)
    socket.consume_sockets(2, "sendspin_mc_websocket_server")(config)
    wifi.enable_runtime_power_save_control()
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(SendspinMcHub),
            cv.Required(CONF_CLIENT_ID): cv.string_strict,
            cv.Required(CONF_CLIENT_NAME): cv.string_strict,
            cv.Required(CONF_SERVER_PORT): cv.port,
            cv.Required(CONF_CONTROL_PORT): cv.port,
            cv.Optional(CONF_TASK_STACK_IN_PSRAM): psram.validate_task_stack_in_psram,
        }
    ),
    cv.only_on_esp32,
    _request_high_performance_networking,
)


async def to_code(config: ConfigType) -> None:
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    cg.add(var.set_client_id(config[CONF_CLIENT_ID]))
    cg.add(var.set_client_name(config[CONF_CLIENT_NAME]))
    cg.add(var.set_server_port(config[CONF_SERVER_PORT]))
    cg.add(var.set_control_port(config[CONF_CONTROL_PORT]))

    if config.get(CONF_TASK_STACK_IN_PSRAM):
        cg.add(var.set_task_stack_in_psram(True))
        psram.request_external_task_stack()

    data = _get_data(config[CONF_ID])

    if data.controller_support:
        cg.add_define("USE_SENDSPIN_MC_CONTROLLER", True)
        cg.add_define("USE_SENDSPIN_MC", True)

    if data.player_support:
        cg.add_define("USE_SENDSPIN_MC_PLAYER", True)
        cg.add_define("USE_SENDSPIN_MC", True)

        player_cfg = data.player_config
        sample_rate = player_cfg[CONF_SAMPLE_RATE]
        bits_per_sample = player_cfg[CONF_BITS_PER_SAMPLE]
        channels = player_cfg[CONF_CHANNELS]

        codecs = [CODEC_FORMAT_FLAC]
        if sample_rate == 48000:
            codecs.append(CODEC_FORMAT_OPUS)
        codecs.append(CODEC_FORMAT_PCM)

        audio_format_structs = [
            cg.StructInitializer(
                AudioSupportedFormatObject,
                ("codec", codec),
                ("channels", channels),
                ("sample_rate", sample_rate),
                ("bit_depth", bits_per_sample),
            )
            for codec in codecs
        ]

        psram_stack = player_cfg.get(CONF_TASK_STACK_IN_PSRAM, False)
        if psram_stack:
            psram.request_external_task_stack()

        player_struct_fields = [
            ("audio_formats", audio_format_structs),
            ("audio_buffer_capacity", player_cfg[CONF_BUFFER_SIZE]),
            ("fixed_delay_us", player_cfg[CONF_FIXED_DELAY]),
            ("initial_static_delay_ms", player_cfg[CONF_INITIAL_STATIC_DELAY]),
            ("psram_stack", psram_stack),
        ]
        if (decode_memory := player_cfg.get(CONF_DECODE_MEMORY)) is not None:
            player_struct_fields.append(
                ("decode_buffer_location", MEMORY_LOCATION_ENUM[decode_memory])
            )
        player_config_struct = cg.StructInitializer(
            PlayerRoleConfig,
            *player_struct_fields,
        )
        cg.add(var.set_player_config(player_config_struct))

    if data.controller_support or data.player_support:
        cg.add_define("USE_SENDSPIN_MC", True)

    # The sendspin-cpp IDF component is provided by YAML so this local component can
    # coexist with ESPHome's built-in sendspin component without overriding it.
    if data.controller_support:
        from esphome.components import esp32

        esp32.add_idf_sdkconfig_option("CONFIG_SENDSPIN_ENABLE_CONTROLLER", True)
    if data.player_support:
        from esphome.components import esp32

        esp32.add_idf_sdkconfig_option("CONFIG_SENDSPIN_ENABLE_PLAYER", True)
