#include "sendspin_mc_text_sensor.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_METADATA) && defined(USE_TEXT_SENSOR)

#include <sendspin/metadata_role.h>

#include <string>

namespace esphome::sendspin_mc {

static const char *const TAG = "sendspin_mc.text_sensor";

void SendspinMcTextSensor::dump_config() { LOG_TEXT_SENSOR("", "Sendspin", this); }

const char *SendspinMcTextSensor::extract_value_(const sendspin::ServerMetadataStateObject &metadata) const {
  switch (this->metadata_type_) {
    case SendspinMcTextMetadataTypes::TITLE:
      if (metadata.title.has_value())
        return metadata.title.value().c_str();
      return nullptr;
    case SendspinMcTextMetadataTypes::ARTIST:
      if (metadata.artist.has_value())
        return metadata.artist.value().c_str();
      return nullptr;
    case SendspinMcTextMetadataTypes::ALBUM:
      if (metadata.album.has_value())
        return metadata.album.value().c_str();
      return nullptr;
    case SendspinMcTextMetadataTypes::ALBUM_ARTIST:
      if (metadata.album_artist.has_value())
        return metadata.album_artist.value().c_str();
      return nullptr;
  }
  return nullptr;
}

// THREAD CONTEXT: Main loop. The registered metadata callback also fires on the main loop
// (SendspinMcHub dispatches metadata from client_->loop()).
void SendspinMcTextSensor::setup() {
  this->parent_->add_metadata_update_callback([this](const sendspin::ServerMetadataStateObject &metadata) {
    if (const char *value = this->extract_value_(metadata)) {
      this->publish_if_changed_(value);
    }
  });
}

// Dedup to avoid frontend churn; TextSensor::publish_state already dedups the string assign but still notifies.
void SendspinMcTextSensor::publish_if_changed_(const char *value) {
  if (this->get_raw_state() != value) {
    this->publish_state(value);
  }
}

}  // namespace esphome::sendspin_mc

#endif
