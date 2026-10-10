#pragma once

#include "esphome/core/defines.h"

#if defined(USE_ESP_IDF) && defined(USE_SENDSPIN_MC_SWITCH)

#include "esphome/components/sendspin_mc/sendspin_mc_hub.h"
#include "esphome/components/switch/switch.h"

namespace esphome::sendspin_mc {

/// @brief Switch that starts and stops the SendspinMc client through the hub (see SendspinMcHub::set_enabled()).
class SendspinMcEnabledSwitch final : public switch_::Switch, public SendspinMcChild {
 public:
  void setup() override;
  void dump_config() override;

 protected:
  void write_state(bool state) override;
};

/// @brief Switch that turns unpaired (Sentinel) access on and off through the hub (see
/// SendspinMcHub::set_unpaired_access_enabled()). The library does not persist the setting, so the switch's restore
/// mode does.
class SendspinMcUnpairedAccessSwitch final : public switch_::Switch, public SendspinMcChild {
 public:
  void setup() override;
  void dump_config() override;

 protected:
  void write_state(bool state) override;
};

}  // namespace esphome::sendspin_mc

#endif
