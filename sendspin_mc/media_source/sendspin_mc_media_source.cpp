#include "sendspin_mc_media_source.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_CONTROLLER) && defined(USE_SENDSPIN_MC_PLAYER)

#include "esphome/components/audio/audio.h"
#include "esphome/core/log.h"

#include <cmath>

namespace esphome::sendspin_mc {

static const char *const TAG = "sendspin_mc.media_source";

void SendspinMcMediaSource::setup() {
  this->player_role_ = this->parent_->get_player_role();
  if (!this->player_role_) {
    ESP_LOGE(TAG, "Failed to get player role from hub");
    this->mark_failed();
    return;
  }

  this->player_role_->update_volume(std::roundf(this->cached_volume_ * 100.0f));
  this->player_role_->update_muted(this->cached_muted_);
  this->player_role_->set_static_delay_adjustable(this->static_delay_adjustable_);
}

void SendspinMcMediaSource::dump_config() {
  ESP_LOGCONFIG(TAG, "Sendspin MC Media Source: static_delay_adjustable=%s",
                YESNO(this->static_delay_adjustable_));
}

void SendspinMcMediaSource::set_static_delay_adjustable(bool adjustable) {
  this->static_delay_adjustable_ = adjustable;
  if (this->player_role_) {
    this->player_role_->set_static_delay_adjustable(adjustable);
  }
}

bool SendspinMcMediaSource::can_handle(const std::string &uri) const {
  return uri == this->parent_->get_current_source_uri();
}

bool SendspinMcMediaSource::play_uri(const std::string &uri) {
  if (!this->is_ready() || this->is_failed() || !this->has_listener()) {
    return false;
  }

  if (this->get_state() != media_source::MediaSourceState::IDLE) {
    ESP_LOGE(TAG, "Cannot play '%s': source is busy", uri.c_str());
    return false;
  }

  if (uri != this->parent_->get_current_source_uri()) {
    ESP_LOGE(TAG, "Invalid URI for %s: '%s'", this->parent_->get_client_id().c_str(), uri.c_str());
    return false;
  }

  this->pending_start_ = false;
  this->set_state_(media_source::MediaSourceState::PLAYING);

  return true;
}

void SendspinMcMediaSource::handle_command(media_source::MediaSourceCommand command) {
  switch (command) {
    case media_source::MediaSourceCommand::STOP: {
      if (!this->pending_start_) {
        ESP_LOGD(TAG, "Received STOP command, updating Sendspin state to EXTERNAL_SOURCE");
        this->parent_->update_state(sendspin::SendspinClientState::EXTERNAL_SOURCE);
      }
      break;
    }
    case media_source::MediaSourceCommand::PLAY:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::PLAY, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::PAUSE:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::PAUSE, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::NEXT:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::NEXT, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::PREVIOUS:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::PREVIOUS, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::REPEAT_ALL:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::REPEAT_ALL, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::REPEAT_ONE:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::REPEAT_ONE, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::REPEAT_OFF:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::REPEAT_OFF, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::SHUFFLE:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::SHUFFLE, std::nullopt, std::nullopt);
      break;
    case media_source::MediaSourceCommand::UNSHUFFLE:
      this->parent_->send_client_command(sendspin::SendspinControllerCommand::UNSHUFFLE, std::nullopt, std::nullopt);
      break;
    default:
      break;
  }
}

void SendspinMcMediaSource::notify_volume_changed(float volume) {
  this->cached_volume_ = volume;
  if (this->player_role_) {
    this->player_role_->update_volume(std::roundf(volume * 100.0f));
  }
}

void SendspinMcMediaSource::notify_mute_changed(bool is_muted) {
  this->cached_muted_ = is_muted;
  if (this->player_role_) {
    this->player_role_->update_muted(is_muted);
  }
}

void SendspinMcMediaSource::notify_audio_played(uint32_t frames, int64_t timestamp) {
  if (this->player_role_) {
    this->player_role_->notify_audio_played(frames, timestamp);
  }
}

size_t SendspinMcMediaSource::on_audio_write(uint8_t *data, size_t length, uint32_t timeout_ms) {
  if (!this->has_listener() || (this->get_state() != media_source::MediaSourceState::PLAYING)) {
    vTaskDelay(pdMS_TO_TICKS(timeout_ms));
    return 0;
  }

  auto &params = this->player_role_->get_current_stream_params();
  if (!params.bit_depth.has_value() || !params.channels.has_value() || !params.sample_rate.has_value()) {
    vTaskDelay(pdMS_TO_TICKS(timeout_ms));
    return 0;
  }
  audio::AudioStreamInfo stream_info(*params.bit_depth, *params.channels, *params.sample_rate);

  return this->write_output(data, length, timeout_ms, stream_info);
}

void SendspinMcMediaSource::on_stream_start() {
  this->parent_->update_state(sendspin::SendspinClientState::SYNCHRONIZED);

  if (!this->pending_start_) {
    this->pending_start_ = true;
    this->request_play_uri_(this->parent_->get_current_source_uri());
  }
}

void SendspinMcMediaSource::on_stream_end() {
  if (this->get_state() != media_source::MediaSourceState::IDLE) {
    this->set_state_(media_source::MediaSourceState::IDLE);
  }
}

void SendspinMcMediaSource::on_volume_changed(uint8_t volume) { this->request_volume_(volume / 100.0f); }

void SendspinMcMediaSource::on_mute_changed(bool muted) { this->request_mute_(muted); }

}  // namespace esphome::sendspin_mc

#endif  // USE_ESP32 && USE_SENDSPIN_MC_PLAYER && USE_SENDSPIN_MC_CONTROLLER
