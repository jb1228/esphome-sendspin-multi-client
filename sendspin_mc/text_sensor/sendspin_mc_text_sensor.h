#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP_IDF) && defined(USE_TEXT_SENSOR)

#include "esphome/components/sendspin_mc/sendspin_mc_hub.h"
#include "esphome/components/text_sensor/text_sensor.h"

#ifdef USE_SENDSPIN_MC_METADATA
#include <sendspin/metadata_role.h>
#endif

namespace esphome::sendspin_mc {

#ifdef USE_SENDSPIN_MC_METADATA

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
#endif  // USE_SENDSPIN_MC_METADATA

class SendspinMcPairingCodeTextSensor final : public SendspinMcChild, public text_sensor::TextSensor {
 public:
  void dump_config() override;
  void setup() override;
};

}  // namespace esphome::sendspin_mc
#endif
