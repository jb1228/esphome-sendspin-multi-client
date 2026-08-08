#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_PLAYER) && defined(USE_SENDSPIN_MC_CONTROLLER)

#include "esphome/core/automation.h"
#include "sendspin_mc_media_source.h"

namespace esphome::sendspin_mc {

template<typename... Ts>
class EnableStaticDelayAdjustmentAction final : public Action<Ts...>, public Parented<SendspinMcMediaSource> {
 public:
  void play(const Ts &...x) override { this->parent_->set_static_delay_adjustable(true); }
};

template<typename... Ts>
class DisableStaticDelayAdjustmentAction final : public Action<Ts...>, public Parented<SendspinMcMediaSource> {
 public:
  void play(const Ts &...x) override { this->parent_->set_static_delay_adjustable(false); }
};

}  // namespace esphome::sendspin_mc

#endif
