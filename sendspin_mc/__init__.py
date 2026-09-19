from dataclasses import dataclass, field

import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.final_validate as fv
from esphome.components import esp32, mdns, network, psram, socket, wifi
from esphome.components.const import CONF_MANUFACTURER
from esphome.const import (
    CONF_BUFFER_SIZE,
    CONF_CLIENT_ID,
    CONF_ESPHOME,
    CONF_FORMAT,
    CONF_HEIGHT,
    CONF_ID,
    CONF_MDNS,
    CONF_MODEL,
    CONF_NAME,
    CONF_PROJECT,
    CONF_SAMPLE_RATE,
    CONF_SOURCE,
    CONF_TASK_STACK_IN_PSRAM,
    CONF_VERSION,
    CONF_WIDTH,
)
from esphome.core import CORE, ID, coroutine_with_priority
from esphome.coroutine import CoroPriority
from esphome.cpp_generator import MockObj, TemplateArgsType
from esphome.types import ConfigType

from esphome import automation

# mdns for autodiscovery
AUTO_LOAD = ["mdns"]
CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["network"]
DOMAIN = "sendspin_mc"
MULTI_CONF = True

CONF_SENDSPIN_MC_ID = "sendspin_mc_id"

CONF_FIRMWARE_VERSION = "firmware_version"

# An empty device information string would be sent to the server as an empty value rather than
# falling back, so reject it instead of silently substituting the fallback. The 127 byte cap keeps
# the length prefix of a protobuf string field to a single byte, matching `esphome: project:`.
DEVICE_INFO_STRING = cv.All(cv.string_strict, cv.Length(min=1), cv.ByteLength(max=127))

CONF_DISPLAY_OFFSET = "display_offset"
CONF_CODECS = "codecs"
MAX_ARTWORK_SLOTS = 4

CONF_CLIENT_NAME = "client_name"
CONF_CONTROL_PORT = "control_port"
CONF_INITIAL_STATIC_DELAY = "initial_static_delay"
CONF_FIXED_DELAY = "fixed_delay"
CONF_DECODE_MEMORY = "decode_memory"
CONF_SERVER_PORT = "server_port"
# Both components share one library; this setting allows matching native's version.
CONF_SENDSPIN_CPP_REF = "sendspin_cpp_ref"

DEFAULT_SENDSPIN_CPP_REF = "0.8.0"

# sendspin-cpp library lives in the global `sendspin` namespace.
sendspin_library_ns = cg.global_ns.namespace("sendspin")

# Library Enums
SendspinCodecFormat = sendspin_library_ns.enum("SendspinCodecFormat", is_class=True)
CODEC_FORMAT_FLAC = SendspinCodecFormat.enum("FLAC")
CODEC_FORMAT_OPUS = SendspinCodecFormat.enum("OPUS")
CODEC_FORMAT_PCM = SendspinCodecFormat.enum("PCM")
CODEC_FORMAT_UNSUPPORTED = SendspinCodecFormat.enum("UNSUPPORTED")

CODEC_FLAC = "flac"
CODEC_OPUS = "opus"
CODEC_PCM = "pcm"

CODECS = {
    CODEC_FLAC: CODEC_FORMAT_FLAC,
    CODEC_OPUS: CODEC_FORMAT_OPUS,
    CODEC_PCM: CODEC_FORMAT_PCM,
}

# Opus only supports 48 kHz audio, so it is left out of the default list at other rates.
DEFAULT_CODECS = [CODEC_FLAC, CODEC_OPUS, CODEC_PCM]
OPUS_SAMPLE_RATE = 48000

SendspinImageFormat = sendspin_library_ns.enum("SendspinImageFormat", is_class=True)
IMAGE_FORMAT_JPEG = SendspinImageFormat.enum("JPEG")
IMAGE_FORMAT_PNG = SendspinImageFormat.enum("PNG")
IMAGE_FORMAT_BMP = SendspinImageFormat.enum("BMP")

SendspinImageSource = sendspin_library_ns.enum("SendspinImageSource", is_class=True)
IMAGE_SOURCE_ALBUM = SendspinImageSource.enum("ALBUM")
IMAGE_SOURCE_ARTIST = SendspinImageSource.enum("ARTIST")

# Library Structs
AudioSupportedFormatObject = sendspin_library_ns.struct("AudioSupportedFormatObject")
PlayerRoleConfig = sendspin_library_ns.struct("PlayerRoleConfig")
ArtworkRoleConfig = sendspin_library_ns.struct("ArtworkRoleConfig")
ImageSlotPreference = sendspin_library_ns.struct("ImageSlotPreference")

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

    artwork_preferences: list[ConfigType] = field(default_factory=list)
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


def _validate_sendspin_cpp_ref(value: str) -> str:
    """Validate the source ref for the sendspin-cpp IDF component."""
    value = cv.string_strict(value)
    if not value.strip():
        raise cv.Invalid("sendspin_mc sendspin_cpp_ref must not be empty")
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

    # TEMPORARY DEVIATION: Merge pre-ID-pass role requests for an implicit single-hub parent.
    # Revisit when native validation can associate these requests directly; see DEVIATIONS.md.
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


def register_artwork_preference(hub_id: ID, config: ConfigType) -> int:
    """Register an artwork slot preference and return the slot it was given.

    A slot is a preference's position in the list, which is also the order the roles are
    advertised to the server in.
    """
    request_artwork_support(hub_id)
    preferences = _get_data(hub_id).artwork_preferences
    if len(preferences) >= MAX_ARTWORK_SLOTS:
        raise cv.Invalid(
            f"Too many Sendspin image slots. Maximum is {MAX_ARTWORK_SLOTS}."
        )
    preferences.append(config)
    return len(preferences) - 1


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
            cv.Optional(
                CONF_SENDSPIN_CPP_REF, default=DEFAULT_SENDSPIN_CPP_REF
            ): _validate_sendspin_cpp_ref,
            cv.Optional(CONF_TASK_STACK_IN_PSRAM): psram.validate_task_stack_in_psram,
            cv.Optional(CONF_MANUFACTURER): DEVICE_INFO_STRING,
            cv.Optional(CONF_MODEL): DEVICE_INFO_STRING,
            cv.Optional(CONF_FIRMWARE_VERSION): DEVICE_INFO_STRING,
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

    sendspin_cpp_refs = {hub[CONF_SENDSPIN_CPP_REF] for hub in hubs}
    if len(sendspin_cpp_refs) > 1:
        refs = ", ".join(repr(ref) for ref in sorted(sendspin_cpp_refs))
        raise cv.Invalid(
            f"Each sendspin_mc hub must use the same sendspin_cpp_ref; got: {refs}"
        )

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


# TEMPORARY DEVIATION: Reconcile shared role flags after native codegen to preserve MC roles.
# Revisit when native/shared codegen aggregates all clients' requirements; see DEVIATIONS.md.
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

    # Device information for the server's client/hello message. Falls back to the project
    # information, which is written as `manufacturer.model`. Anything still unset keeps the
    # default the hub itself applies: the ESPHome name and version.
    project = CORE.config[CONF_ESPHOME].get(CONF_PROJECT, {})
    project_manufacturer, _, project_model = project.get(CONF_NAME, "").partition(".")
    for value, setter in (
        (config.get(CONF_MANUFACTURER) or project_manufacturer, var.set_manufacturer),
        (config.get(CONF_MODEL) or project_model, var.set_model),
        (
            config.get(CONF_FIRMWARE_VERSION) or project.get(CONF_VERSION),
            var.set_firmware_version,
        ),
    ):
        if value:
            cg.add(setter(value))

    # A switch controls only its parent. Hubs without one start enabled.
    if not any(
        item.get("platform") == DOMAIN and item[CONF_SENDSPIN_MC_ID] == config[CONF_ID]
        for item in CORE.config.get("switch", [])
    ):
        cg.add(var.set_enabled(True))

    if mdns.request_service_enable_disable():
        mdns_var = await cg.get_variable(CORE.config[CONF_MDNS][CONF_ID])
        cg.add(var.set_mdns(mdns_var))
        # Multiple named services share the same type/protocol and local hostname.
        esp32.add_idf_sdkconfig_option("CONFIG_MDNS_MULTIPLE_INSTANCE", True)

    # sendspin-cpp library
    esp32.add_idf_component(
        name="sendspin/sendspin-cpp", ref=config[CONF_SENDSPIN_CPP_REF]
    )

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

    if artwork_support:
        cg.add(var.set_artwork_support(data.artwork_support))

    if data.artwork_support:
        # require_frame_done is always on: SendspinImageSlot always acks a delivery, either
        # immediately or from the transition_finished action.
        preference_structs = [
            cg.StructInitializer(
                ImageSlotPreference,
                ("source", pref[CONF_SOURCE]),
                ("format", pref[CONF_FORMAT]),
                ("width", pref[CONF_WIDTH]),
                ("height", pref[CONF_HEIGHT]),
                ("require_frame_done", True),
                ("display_offset_ms", pref[CONF_DISPLAY_OFFSET]),
            )
            for pref in data.artwork_preferences
        ]

        artwork_psram_stack = bool(config.get(CONF_TASK_STACK_IN_PSRAM))
        artwork_config = cg.StructInitializer(
            ArtworkRoleConfig,
            ("preferred_formats", preference_structs),
            ("psram_stack", artwork_psram_stack),
        )
        cg.add(var.set_artwork_config(artwork_config))

    if controller_support:
        cg.add(var.set_controller_support(data.controller_support))

    if metadata_support:
        cg.add(var.set_metadata_support(data.metadata_support))

    if player_support:
        cg.add(var.set_player_support(data.player_support))

    if data.player_support:
        # Configures the player role. Each configured codec is advertised for 16 bits per sample
        # mono and stereo at the configured sample rate. The order is a preference order, both for
        # the codecs themselves and for stereo over mono.
        player_cfg = data.player_config
        sample_rate = player_cfg[CONF_SAMPLE_RATE]

        codecs = [CODECS[codec] for codec in player_cfg[CONF_CODECS]]

        def _audio_format(codec: MockObj, channels: int) -> cg.StructInitializer:
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
