#include "sendspin_mc_sensor.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_METADATA) && defined(USE_SENSOR)

#include <sendspin/metadata_role.h>

namespace esphome::sendspin_mc {

static const char *const TAG = "sendspin_mc.sensor";

// --- SendspinMcTrackProgressSensor ---

void SendspinMcTrackProgressSensor::dump_config() {
  LOG_SENSOR("", "Track Progress", this);
  LOG_UPDATE_INTERVAL(this);
}

// THREAD CONTEXT: Main loop. The registered metadata callback also fires on the main loop
// (SendspinMcHub dispatches metadata from client_->loop()).
void SendspinMcTrackProgressSensor::setup() {
  this->parent_->add_metadata_update_callback([this](const sendspin::ServerMetadataStateObject &metadata) {
    if (!metadata.progress.has_value()) {
      return;
    }
    const auto &progress = metadata.progress.value();
    if (progress.playback_speed == 0) {
      // Paused: freeze progress at the reported position and stop polling to save cycles.
      this->stop_poller();
      this->publish_state(progress.track_progress);
    } else {
      // Resumed: publish the fresh interpolated position immediately so the frontend doesn't show a stale
      // paused value until the next poll tick.
      this->publish_state(this->parent_->get_track_progress_ms());
      this->start_poller();
    }
  });
}

// THREAD CONTEXT: Main loop.
// Sendspin only pushes progress on state changes (play/pause/seek/speed change), not continuously during
// playback. The hub helper interpolates the current position from the last server update and the playback
// speed, giving us a fresh value on every poll.
void SendspinMcTrackProgressSensor::update() { this->publish_state(this->parent_->get_track_progress_ms()); }

// --- SendspinMcMetadataSensor ---

void SendspinMcMetadataSensor::dump_config() {
  switch (this->metadata_type_) {
    case SendspinMcNumericMetadataTypes::TRACK_DURATION:
      LOG_SENSOR("", "Track Duration", this);
      break;
    case SendspinMcNumericMetadataTypes::YEAR:
      LOG_SENSOR("", "Year", this);
      break;
    case SendspinMcNumericMetadataTypes::TRACK:
      LOG_SENSOR("", "Track", this);
      break;
  }
}

std::optional<float> SendspinMcMetadataSensor::extract_value_(
    const sendspin::ServerMetadataStateObject &metadata) const {
  switch (this->metadata_type_) {
    case SendspinMcNumericMetadataTypes::TRACK_DURATION:
      if (metadata.progress.has_value())
        return metadata.progress.value().track_duration;
      return std::nullopt;
    case SendspinMcNumericMetadataTypes::YEAR:
      if (metadata.year.has_value())
        return metadata.year.value();
      return std::nullopt;
    case SendspinMcNumericMetadataTypes::TRACK:
      if (metadata.track.has_value())
        return metadata.track.value();
      return std::nullopt;
  }
  return std::nullopt;
}

// THREAD CONTEXT: Main loop. The registered metadata callback also fires on the main loop
// (SendspinMcHub dispatches metadata from client_->loop()).
void SendspinMcMetadataSensor::setup() {
  this->parent_->add_metadata_update_callback([this](const sendspin::ServerMetadataStateObject &metadata) {
    if (auto value = this->extract_value_(metadata)) {
      this->publish_if_changed_(*value);
    }
  });
}

// Dedup to avoid frontend churn; Sensor::publish_state always notifies without checking for changes.
void SendspinMcMetadataSensor::publish_if_changed_(float value) {
  if (this->get_raw_state() != value) {
    this->publish_state(value);
  }
}

}  // namespace esphome::sendspin_mc

#endif
