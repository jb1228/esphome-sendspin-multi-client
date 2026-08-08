from dataclasses import dataclass, field

from esphome import automation
import esphome.codegen as cg
from esphome.components import esp32, network, psram, socket, wifi
import esphome.config_validation as cv
import esphome.final_validate as fv
from esphome.const import (
    CONF_BUFFER_SIZE,
    CONF_CLIENT_ID,
    CONF_ID,
    CONF_NAME,
    CONF_SAMPLE_RATE,
    CONF_TASK_STACK_IN_PSRAM,
)
from esphome.core import CORE, ID, coroutine_with_priority
from esphome.coroutine import CoroPriority
from esphome.cpp_generator import TemplateArgsType
from esphome.types import ConfigType

# mdns for autodiscovery
AUTO_LOAD = ["mdns"]
CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["network"]
DOMAIN = "sendspin_mc"
MULTI_CONF = True

CONF_SENDSPIN_MC_ID = "sendspin_mc_id"

CONF_CLIENT_NAME = "client_name"
CONF_CONTROL_PORT = "control_port"
CONF_INITIAL_STATIC_DELAY = "initial_static_delay"
CONF_FIXED_DELAY = "fixed_delay"
CONF_DECODE_MEMORY = "decode_memory"
CONF_SERVER_PORT = "server_port"

# sendspin-cpp library lives in the global `sendspin` namespace.
sendspin_library_ns = cg.global_ns.namespace("sendspin")

# Library Enums
SendspinCodecFormat = sendspin_library_ns.enum("SendspinCodecFormat", is_class=True)
CODEC_FORMAT_FLAC = SendspinCodecFormat.enum("FLAC")
CODEC_FORMAT_OPUS = SendspinCodecFormat.enum("OPUS")
CODEC_FORMAT_PCM = SendspinCodecFormat.enum("PCM")
CODEC_FORMAT_UNSUPPORTED = SendspinCodecFormat.enum("UNSUPPORTED")

# Library Structs
AudioSupportedFormatObject = sendspin_library_ns.struct("AudioSupportedFormatObject")
PlayerRoleConfig = sendspin_library_ns.struct("PlayerRoleConfig")

# MemoryLocation enum (from sendspin/types.h) controls SPIRAM-vs-internal-RAM placement
# preference for the player role's transfer buffers.
SendspinMemoryLocation = sendspin_library_ns.enum("MemoryLocation", is_class=True)

MEMORY_PSRAM = "psram"
MEMORY_INTERNAL = "internal"
MEMORY_LOCATIONS = [MEMORY_PSRAM, MEMORY_INTERNAL]
MEMORY_LOCATION_ENUM = {
    MEMORY_PSRAM: SendspinMemoryLocation.PREFER_EXTERNAL,
    MEMORY_INTERNAL: SendspinMemoryLocation.PREFER_INTERNAL,
}

sendspin_mc_ns = cg.esphome_ns.namespace("sendspin_mc")
SendspinMcHub = sendspin_mc_ns.class_(
    "SendspinMcHub",
    cg.Component,
)


SendspinMcSwitchCommandAction = sendspin_mc_ns.class_(
    "SendspinMcSwitchCommandAction",
    automation.Action,
    cg.Parented.template(SendspinMcHub),
)


@dataclass
class SendspinMcConfiguration:
    artwork_support: bool = False
    controller_support: bool = False
    metadata_support: bool = False
    player_support: bool = False
    visualizer_support: bool = False

    player_config: ConfigType | None = None


@dataclass
class SendspinMcComponentData:
    hubs: dict[str | None, SendspinMcConfiguration] = field(default_factory=dict)
    role_defines_emitted: bool = False
    sdkconfig_job_scheduled: bool = False


def _validate_client_id(value: str) -> str:
    """Validate the configured Sendspin identity and URI path segment."""
    value = cv.string_strict(value)
    if not value:
        raise cv.Invalid("sendspin_mc client_id must not be empty")
    if "/" in value:
        raise cv.Invalid("sendspin_mc client_id must not contain '/'")
    return value


def _validate_mdns_instance_name(value: str) -> str:
    """Validate the configured DNS-SD service-instance label."""
    value = cv.string_strict(value)
    if not value:
        raise cv.Invalid("sendspin_mc client_name must not be empty")
    if len(value.encode("utf-8")) > 63:
        raise cv.Invalid("sendspin_mc client_name must be at most 63 UTF-8 bytes")
    return value


def _get_all_data() -> SendspinMcComponentData:
    if DOMAIN not in CORE.data:
        CORE.data[DOMAIN] = SendspinMcComponentData()
    return CORE.data[DOMAIN]


def _get_data(hub_id: ID) -> SendspinMcConfiguration:
    hubs = _get_all_data().hubs
    key = hub_id.id
    if key not in hubs:
        hubs[key] = SendspinMcConfiguration()
    return hubs[key]


def _get_codegen_data(hub_id: ID) -> SendspinMcConfiguration:
    """Return role data for a resolved hub, including a single-hub implicit reference."""
    hubs = _get_all_data().hubs
    data = hubs.setdefault(hub_id.id, SendspinMcConfiguration())
    implicit = hubs.get(None)
    if implicit is None or implicit is data:
        return data

    # ESPHome only resolves an omitted parent ID when there is exactly one matching hub.
    # Merge that pre-ID-pass bucket into the resolved hub without changing multi-hub behavior.
    if len(CORE.config.get(DOMAIN, [])) == 1:
        data.artwork_support |= implicit.artwork_support
        data.controller_support |= implicit.controller_support
        data.metadata_support |= implicit.metadata_support
        data.player_support |= implicit.player_support
        data.visualizer_support |= implicit.visualizer_support
        if data.player_config is None:
            data.player_config = implicit.player_config
    return data


def request_artwork_support(hub_id: ID) -> None:
    """Request artwork role support for Sendspin."""
    _get_data(hub_id).artwork_support = True


def request_controller_support(hub_id: ID) -> None:
    """Request controller role support for Sendspin."""
    _get_data(hub_id).controller_support = True


def request_metadata_support(hub_id: ID) -> None:
    """Request metadata role support for Sendspin."""
    _get_data(hub_id).metadata_support = True


def request_player_support(hub_id: ID) -> None:
    """Request player role support for Sendspin."""
    _get_data(hub_id).player_support = True


def request_visualizer_support(hub_id: ID) -> None:
    """Request visualizer role support for Sendspin."""
    _get_data(hub_id).visualizer_support = True


def register_player_config(hub_id: ID, config: ConfigType) -> None:
    """Register the player role config from the media source subcomponent."""
    data = _get_data(hub_id)
    request_player_support(hub_id)
    if data.player_config is not None:
        raise cv.Invalid(
            f"Only one sendspin_mc media_source player configuration is supported for {hub_id.id or 'the implicit hub'}"
        )
    data.player_config = config


def _request_high_performance_networking(config: ConfigType) -> ConfigType:
    """Request high performance networking for Sendspin streaming.

    Also enables wake_loop_threadsafe support for fast defer() callbacks
    from background threads (WebSocket handler, image decoder).
    """
    network.require_high_performance_networking()
    # Socket consumption varies by mode:
    # - Server mode: 1 listening socket + 4 client connections (established connection, unproven connections, and a spare)
    # - Client mode: 1 outbound connection
    socket.consume_sockets(
        1, "sendspin_websocket_server", socket.SocketType.TCP_LISTEN
    )(config)
    socket.consume_sockets(4, "sendspin_websocket_server")(config)
    socket.consume_sockets(1, "sendspin_websocket_client")(config)

    wifi.enable_runtime_power_save_control()
    wifi.enable_runtime_roaming_suppression()
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(SendspinMcHub),
            cv.Required(CONF_CLIENT_ID): _validate_client_id,
            cv.Required(CONF_CLIENT_NAME): _validate_mdns_instance_name,
            cv.Required(CONF_SERVER_PORT): cv.port,
            cv.Required(CONF_CONTROL_PORT): cv.port,
            cv.Optional(CONF_TASK_STACK_IN_PSRAM): psram.validate_task_stack_in_psram,
        }
    ),
    cv.only_on_esp32,
    _request_high_performance_networking,
)


def _final_validate(config: ConfigType) -> ConfigType:
    """Reject identity and TCP port collisions before code generation."""
    full_config = fv.full_config.get()
    hubs = full_config[DOMAIN]

    # This hook runs once per MULTI_CONF entry. Perform the aggregate check once.
    if config[CONF_ID].id != hubs[0][CONF_ID].id:
        return config

    for field_name, label in (
        (CONF_CLIENT_ID, "client ID"),
        (CONF_CLIENT_NAME, "client name"),
    ):
        seen: set[str] = set()
        for hub in hubs:
            value = hub[field_name]
            comparison_value = (
                value.casefold() if field_name == CONF_CLIENT_NAME else value
            )
            if comparison_value in seen:
                raise cv.Invalid(
                    f"Each sendspin_mc {label} must be unique; duplicate value: {value!r}"
                )
            seen.add(comparison_value)

    used_ports: dict[int, str] = {}
    if "sendspin" in full_config:
        core_mdns_name = full_config["esphome"][CONF_NAME]
        for hub in hubs:
            if hub[CONF_CLIENT_NAME].casefold() == core_mdns_name.casefold():
                raise cv.Invalid(
                    f"sendspin_mc client name {hub[CONF_CLIENT_NAME]!r} conflicts with the official sendspin mDNS instance"
                )
        used_ports[8928] = "the official sendspin server"
        used_ports[32769] = "the official sendspin HTTP control socket"

    for hub in hubs:
        hub_name = hub[CONF_CLIENT_NAME]
        for field_name, label in (
            (CONF_SERVER_PORT, "server port"),
            (CONF_CONTROL_PORT, "control port"),
        ):
            port = hub[field_name]
            if owner := used_ports.get(port):
                raise cv.Invalid(
                    f"sendspin_mc {label} {port} for {hub_name!r} conflicts with {owner}"
                )
            used_ports[port] = f"sendspin_mc hub {hub_name!r}"

    return config


FINAL_VALIDATE_SCHEMA = _final_validate


def _request_controller_role(config: ConfigType) -> ConfigType:
    """Request the controller role for the sendspin.switch action."""
    request_controller_support(config[CONF_ID])
    return config


SENDSPIN_SIMPLE_ACTION_SCHEMA = cv.All(
    automation.maybe_simple_id(
        cv.Schema(
            {
                cv.GenerateID(): cv.use_id(SendspinMcHub),
            }
        )
    ),
    _request_controller_role,
)


@automation.register_action(
    "sendspin_mc.switch",
    SendspinMcSwitchCommandAction,
    SENDSPIN_SIMPLE_ACTION_SCHEMA,
    synchronous=True,
)
async def sendspin_switch_to_code(
    config: ConfigType,
    action_id: ID,
    template_arg: cg.TemplateArguments,
    args: TemplateArgsType,
):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var


@coroutine_with_priority(CoroPriority.FINAL)
async def _finalize_sendspin_sdkconfig() -> None:
    """Reconcile shared sendspin-cpp Kconfig flags after core and MC codegen."""
    configurations = _get_all_data().hubs.values()
    requested = {
        "ARTWORK": any(data.artwork_support for data in configurations),
        "CONTROLLER": any(data.controller_support for data in configurations),
        "METADATA": any(data.metadata_support for data in configurations),
        "PLAYER": any(data.player_support for data in configurations),
        "VISUALIZER": any(data.visualizer_support for data in configurations),
    }
    core_sendspin_present = "sendspin" in CORE.config

    # If core sendspin is present, leave roles used only by it untouched. A role used
    # by sendspin_mc must be forced on after core's own true/false decisions.
    for role, enabled in requested.items():
        if enabled or not core_sendspin_present:
            esp32.add_idf_sdkconfig_option(f"CONFIG_SENDSPIN_ENABLE_{role}", enabled)
    if not core_sendspin_present:
        esp32.add_idf_sdkconfig_option("CONFIG_SENDSPIN_ENABLE_COLOR", False)


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

    # sendspin-cpp library
    esp32.add_idf_component(name="sendspin/sendspin-cpp", ref="0.7.0")

    component_data = _get_all_data()
    if not component_data.sdkconfig_job_scheduled:
        component_data.sdkconfig_job_scheduled = True
        CORE.add_job(_finalize_sendspin_sdkconfig)

    data = _get_codegen_data(config[CONF_ID])
    all_data = component_data.hubs.values()

    artwork_support = any(item.artwork_support for item in all_data)
    controller_support = any(item.controller_support for item in all_data)
    metadata_support = any(item.metadata_support for item in all_data)
    player_support = any(item.player_support for item in all_data)
    visualizer_support = any(item.visualizer_support for item in all_data)

    # Compile the union once, then enable each role only on its owning hub.
    if not component_data.role_defines_emitted:
        component_data.role_defines_emitted = True
        if artwork_support:
            cg.add_define("USE_SENDSPIN_MC_ARTWORK", True)
        if controller_support:
            cg.add_define("USE_SENDSPIN_MC_CONTROLLER", True)
        if metadata_support:
            cg.add_define("USE_SENDSPIN_MC_METADATA", True)
        if player_support:
            cg.add_define("USE_SENDSPIN_MC_PLAYER", True)
        if visualizer_support:
            cg.add_define("USE_SENDSPIN_MC_VISUALIZER", True)

    if controller_support:
        cg.add(var.set_controller_support(data.controller_support))

    if metadata_support:
        cg.add(var.set_metadata_support(data.metadata_support))

    if player_support:
        cg.add(var.set_player_support(data.player_support))

    if data.player_support:
        # Configures the player role. We always assume support for 16 bits per sample mono and stereo FLAC, Opus, and PCM at the configured sample rate
        # (with Opus only supported at 48 kHz since that's the only sample rate it supports). Users can configure the specific formats via the Sendspin server
        player_cfg = data.player_config
        sample_rate = player_cfg[CONF_SAMPLE_RATE]

        # OPUS only supports 48 kHz audio
        codecs = [CODEC_FORMAT_FLAC]
        if sample_rate == 48000:
            codecs.append(CODEC_FORMAT_OPUS)
        codecs.append(CODEC_FORMAT_PCM)

        def _audio_format(codec, channels):
            return cg.StructInitializer(
                AudioSupportedFormatObject,
                ("codec", codec),
                ("channels", channels),
                ("sample_rate", sample_rate),
                ("bit_depth", 16),
            )

        audio_format_structs = [
            _audio_format(codec, channels) for codec in codecs for channels in (2, 1)
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
