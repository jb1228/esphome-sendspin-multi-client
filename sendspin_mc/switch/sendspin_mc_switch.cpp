#include "sendspin_mc_switch.h"

#ifdef USE_ESP32

#include "esphome/core/log.h"

namespace esphome::sendspin_mc {

static const char *const TAG = "sendspin_mc.switch";

void SendspinMcSwitch::setup() {
  // The hub waits for this request, so a restore mode without a state still has to answer.
  this->control(this->get_initial_state_with_restore_mode().value_or(true));
}

void SendspinMcSwitch::dump_config() { LOG_SWITCH("", "Sendspin Switch", this); }

// THREAD CONTEXT: Main loop
void SendspinMcSwitch::write_state(bool state) {
  this->parent_->set_enabled(state);
  this->publish_state(state);
}

}  // namespace esphome::sendspin_mc

#endif  // USE_ESP32
