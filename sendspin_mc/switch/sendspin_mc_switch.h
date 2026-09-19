#pragma once

#include "esphome/core/defines.h"

#ifdef USE_ESP32

#include "esphome/components/sendspin_mc/sendspin_mc_hub.h"
#include "esphome/components/switch/switch.h"

namespace esphome::sendspin_mc {

/// @brief Switch that starts and stops the Sendspin client through the hub (see SendspinMcHub::set_enabled()).
class SendspinMcSwitch final : public switch_::Switch, public SendspinMcChild {
 public:
  void setup() override;
  void dump_config() override;

 protected:
  void write_state(bool state) override;
};

}  // namespace esphome::sendspin_mc

#endif  // USE_ESP32
