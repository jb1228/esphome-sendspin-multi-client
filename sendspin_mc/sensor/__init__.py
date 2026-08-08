import esphome.codegen as cg
from esphome.components import sensor
import esphome.config_validation as cv
from esphome.const import (
    CONF_ID,
    CONF_TYPE,
    CONF_YEAR,
    STATE_CLASS_MEASUREMENT,
    UNIT_MILLISECOND,
)
from esphome.types import ConfigType

from .. import (
    CONF_SENDSPIN_MC_ID,
    SendspinMcHub,
    request_metadata_support,
    sendspin_mc_ns,
)

CODEOWNERS = ["@jb1228"]
DEPENDENCIES = ["sendspin_mc"]

CONF_TRACK = "track"
CONF_TRACK_PROGRESS = "track_progress"
CONF_TRACK_DURATION = "track_duration"

SendspinMcTrackProgressSensor = sendspin_mc_ns.class_(
    "SendspinMcTrackProgressSensor",
    sensor.Sensor,
    cg.PollingComponent,
)
SendspinMcMetadataSensor = sendspin_mc_ns.class_(
    "SendspinMcMetadataSensor",
    sensor.Sensor,
    cg.Component,
)

SendspinMcNumericMetadataTypes = sendspin_mc_ns.enum(
    "SendspinMcNumericMetadataTypes", is_class=True
)
_METADATA_TYPE_ENUM = {
    CONF_TRACK_DURATION: SendspinMcNumericMetadataTypes.TRACK_DURATION,
    CONF_YEAR: SendspinMcNumericMetadataTypes.YEAR,
    CONF_TRACK: SendspinMcNumericMetadataTypes.TRACK,
}


def _request_roles(config: ConfigType) -> ConfigType:
    """Request the necessary Sendspin roles for the sensor."""
    request_metadata_support(config[CONF_SENDSPIN_MC_ID])

    return config


_HUB_ID_SCHEMA = cv.Schema(
    {cv.GenerateID(CONF_SENDSPIN_MC_ID): cv.use_id(SendspinMcHub)}
)


def _metadata_schema(**sensor_kwargs):
    """Schema for event-driven numeric metadata sensors (duration/year/track)."""
    return (
        sensor.sensor_schema(
            SendspinMcMetadataSensor,
            accuracy_decimals=0,
            **sensor_kwargs,
        )
        .extend(_HUB_ID_SCHEMA)
        .extend(cv.COMPONENT_SCHEMA)
    )


CONFIG_SCHEMA = cv.All(
    cv.typed_schema(
        {
            CONF_TRACK_PROGRESS: sensor.sensor_schema(
                SendspinMcTrackProgressSensor,
                accuracy_decimals=0,
                state_class=STATE_CLASS_MEASUREMENT,
                unit_of_measurement=UNIT_MILLISECOND,
            )
            .extend(_HUB_ID_SCHEMA)
            .extend(cv.polling_component_schema("1s")),
            CONF_TRACK_DURATION: _metadata_schema(
                state_class=STATE_CLASS_MEASUREMENT,
                unit_of_measurement=UNIT_MILLISECOND,
            ),
            CONF_YEAR: _metadata_schema(),
            CONF_TRACK: _metadata_schema(),
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
    await sensor.register_sensor(var, config)

    if (metadata_type := _METADATA_TYPE_ENUM.get(config[CONF_TYPE])) is not None:
        cg.add(var.set_metadata_type(metadata_type))
