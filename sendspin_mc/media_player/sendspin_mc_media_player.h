#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP32) && defined(USE_MEDIA_PLAYER) && defined(USE_SENDSPIN_MC_CONTROLLER)

#include "esphome/components/sendspin_mc/sendspin_mc_hub.h"
#include "esphome/components/media_player/media_player.h"

namespace esphome::sendspin_mc {

class SendspinMcMediaPlayer : public SendspinMcChild, public media_player::MediaPlayer {
 public:
  void setup() override;
  media_player::MediaPlayerTraits get_traits() override;
  bool is_muted() const override { return this->muted_; }
  void dump_config() override;

  void set_volume_increment(float volume_increment) { this->volume_increment_ = volume_increment; }

 protected:
  void control(const media_player::MediaPlayerCall &call) override;

  bool muted_{false};
  float volume_increment_{0.05f};
};

}  // namespace esphome::sendspin_mc

#endif
