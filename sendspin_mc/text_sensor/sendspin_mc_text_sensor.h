#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_METADATA) && defined(USE_TEXT_SENSOR)

#include "esphome/components/sendspin_mc/sendspin_mc_hub.h"
#include "esphome/components/text_sensor/text_sensor.h"

#include <sendspin/metadata_role.h>

namespace esphome::sendspin_mc {

enum class SendspinMcTextMetadataTypes {
  TITLE,
  ARTIST,
  ALBUM,
  ALBUM_ARTIST,
};

class SendspinMcTextSensor final : public SendspinMcChild, public text_sensor::TextSensor {
 public:
  void dump_config() override;
  void setup() override;

  void set_metadata_type(SendspinMcTextMetadataTypes metadata_type) { this->metadata_type_ = metadata_type; }

 protected:
  const char *extract_value_(const sendspin::ServerMetadataStateObject &metadata) const;
  void publish_if_changed_(const char *value);

  SendspinMcTextMetadataTypes metadata_type_;
};

}  // namespace esphome::sendspin_mc
#endif
