#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_PLAYER) && defined(USE_SENDSPIN_MC_CONTROLLER)

#include "sendspin_mc_media_source.h"

namespace esphome::sendspin_mc {

template<typename... Ts>
class EnableStaticDelayAdjustmentAction : public Action<Ts...>, public Parented<SendspinMcMediaSource> {
 public:
  void play(Ts... x) override { this->parent_->set_static_delay_adjustable(true); }
};

template<typename... Ts>
class DisableStaticDelayAdjustmentAction : public Action<Ts...>, public Parented<SendspinMcMediaSource> {
 public:
  void play(Ts... x) override { this->parent_->set_static_delay_adjustable(false); }
};

}  // namespace esphome::sendspin_mc

#endif  // USE_ESP32 && USE_SENDSPIN_MC_PLAYER && USE_SENDSPIN_MC_CONTROLLER
