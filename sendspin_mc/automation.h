#pragma once

#include "esphome/core/defines.h"

#ifdef USE_ESP32

#include "esphome/core/automation.h"
#include "sendspin_mc_hub.h"

namespace esphome::sendspin_mc {

#ifdef USE_SENDSPIN_MC_CONTROLLER
template<typename... Ts>
class SendspinMcSwitchCommandAction final : public Action<Ts...>, public Parented<SendspinMcHub> {
 public:
  void play(const Ts &...x) override {
    // Clear any EXTERNAL_SOURCE state so the switch command is followed
    this->parent_->update_state(sendspin::SendspinClientState::SYNCHRONIZED);
    this->parent_->send_client_command(sendspin::SendspinControllerCommand::SWITCH);
  }
};
#endif  // USE_SENDSPIN_MC_CONTROLLER

}  // namespace esphome::sendspin_mc

#endif  // USE_ESP32
