#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_CONTROLLER) && defined(USE_SENDSPIN_MC_PLAYER)

#include "esphome/components/sendspin_mc/sendspin_mc_hub.h"

#include "esphome/components/media_source/media_source.h"

#include <sendspin/player_role.h>

namespace esphome::sendspin_mc {

class SendspinMcMediaSource : public SendspinMcChild,
                              public media_source::MediaSource,
                              public sendspin::PlayerRoleListener {
 public:
  void setup() override;
  void dump_config() override;

  void set_static_delay_adjustable(bool adjustable);

  bool play_uri(const std::string &uri) override;
  void handle_command(media_source::MediaSourceCommand command) override;
  bool can_handle(const std::string &uri) const override;
  bool has_internal_playlist() const override { return true; }

  void notify_volume_changed(float volume) override;
  void notify_mute_changed(bool is_muted) override;
  void notify_audio_played(uint32_t frames, int64_t timestamp) override;

 protected:
  size_t on_audio_write(uint8_t *data, size_t length, uint32_t timeout_ms) override;
  void on_stream_start() override;
  void on_stream_end() override;
  void on_volume_changed(uint8_t volume) override;
  void on_mute_changed(bool muted) override;

  sendspin::PlayerRole *player_role_{nullptr};

  float cached_volume_{0.0f};

  bool cached_muted_{false};
  bool pending_start_{false};
  bool static_delay_adjustable_{false};
};

}  // namespace esphome::sendspin_mc

#endif
