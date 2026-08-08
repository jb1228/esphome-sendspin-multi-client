#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_METADATA) && defined(USE_SENSOR)

#include "esphome/components/sendspin_mc/sendspin_mc_hub.h"
#include "esphome/components/sensor/sensor.h"

#include <optional>

namespace esphome::sendspin_mc {

class SendspinMcTrackProgressSensor final : public sensor::Sensor, public SendspinMcPollingChild {
 public:
  void dump_config() override;
  void setup() override;
  void update() override;
};

enum class SendspinMcNumericMetadataTypes {
  TRACK_DURATION,
  YEAR,
  TRACK,
};

class SendspinMcMetadataSensor final : public sensor::Sensor, public SendspinMcChild {
 public:
  void dump_config() override;
  void setup() override;

  void set_metadata_type(SendspinMcNumericMetadataTypes metadata_type) { this->metadata_type_ = metadata_type; }

 protected:
  std::optional<float> extract_value_(const sendspin::ServerMetadataStateObject &metadata) const;
  void publish_if_changed_(float value);

  SendspinMcNumericMetadataTypes metadata_type_;
};

}  // namespace esphome::sendspin_mc
#endif
