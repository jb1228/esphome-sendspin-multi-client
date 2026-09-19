#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP32) && defined(USE_SENDSPIN_MC_ARTWORK)

#include "esphome/core/automation.h"
#include "sendspin_mc_image.h"

namespace esphome::sendspin_mc {

template<typename... Ts>
class SendspinMcImageTransitionFinishedAction final : public Action<Ts...>, public Parented<SendspinMcImageSlot> {
 public:
  void play(const Ts &...x) override { this->parent_->transition_finished(); }
};

}  // namespace esphome::sendspin_mc

#endif
