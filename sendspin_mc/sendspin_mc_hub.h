#pragma once

#include "esphome/core/defines.h"

#ifdef USE_ESP32

#include "esphome/core/component.h"
#include "esphome/core/helpers.h"
#include "esphome/core/preferences.h"

#include <sendspin/client.h>
#include <sendspin/config.h>
#include <sendspin/types.h>

#ifdef USE_SENDSPIN_MC_CONTROLLER
#include <sendspin/controller_role.h>
#endif
#ifdef USE_SENDSPIN_MC_PLAYER
#include <sendspin/player_role.h>
#endif

#include <functional>
#include <memory>
#include <optional>
#include <string>

namespace esphome::sendspin_mc {

namespace sendspin_mc_priority {
// This hub registers an additional named _sendspin._tcp mDNS service at runtime,
// so it must start after ESPHome's mDNS component has initialized the responder.
inline constexpr float HUB = esphome::setup_priority::AFTER_CONNECTION - 1.0f;
inline constexpr float CHILD = HUB - 1.0f;
}  // namespace sendspin_mc_priority

struct LastPlayedServerPref {
  uint32_t server_id_hash;
};

#ifdef USE_SENDSPIN_MC_PLAYER
struct StaticDelayPref {
  uint16_t delay_ms;
};
#endif

class SendspinMcHub final : public Component,
#ifdef USE_SENDSPIN_MC_CONTROLLER
                            public sendspin::ControllerRoleListener,
#endif
                            public sendspin::SendspinClientListener,
                            public sendspin::SendspinNetworkProvider,
                            public sendspin::SendspinPersistenceProvider {
 public:
  float get_setup_priority() const override { return sendspin_mc_priority::HUB; }
  void setup() override;
  void loop() override;
  void dump_config() override;

  void connect_to_server(const std::string &url);
  void disconnect_from_server(sendspin::SendspinGoodbyeReason reason);
  void update_state(sendspin::SendspinClientState state);

  void set_client_id(const std::string &client_id) { this->client_id_ = client_id; }
  void set_client_name(const std::string &client_name) { this->client_name_ = client_name; }
  void set_server_port(uint16_t server_port) { this->server_port_ = server_port; }
  void set_control_port(uint16_t control_port) { this->control_port_ = control_port; }
  void set_task_stack_in_psram(bool task_stack_in_psram) { this->task_stack_in_psram_ = task_stack_in_psram; }

  const std::string &get_client_id() const { return this->client_id_; }
  std::string get_current_source_uri() const { return "sendspin_mc://" + this->client_id_ + "/current"; }

  template<typename F> void add_group_update_callback(F &&callback) {
    this->group_update_callbacks_.add(std::forward<F>(callback));
  }

#ifdef USE_SENDSPIN_MC_CONTROLLER
  void send_client_command(sendspin::SendspinControllerCommand command, std::optional<uint8_t> volume = std::nullopt,
                           std::optional<bool> mute = std::nullopt);

  template<typename F> void add_controller_state_callback(F &&callback) {
    this->controller_state_callbacks_.add(std::forward<F>(callback));
  }
#endif

#ifdef USE_SENDSPIN_MC_PLAYER
  void set_listener(sendspin::PlayerRoleListener *listener) { this->player_listener_ = listener; }
  void set_player_config(const sendspin::PlayerRoleConfig &config) { this->player_config_ = config; }
  sendspin::PlayerRole *get_player_role();
#endif

 protected:
  sendspin::SendspinClientConfig build_client_config_();
  void register_mdns_service_();

  void on_group_update(const sendspin::GroupUpdateObject &group) override;
  void on_request_high_performance() override;
  void on_release_high_performance() override;

  bool is_network_ready() override;

  bool save_last_server_hash(uint32_t hash) override;
  std::optional<uint32_t> load_last_server_hash() override;

#ifdef USE_SENDSPIN_MC_CONTROLLER
  sendspin::ControllerRole *controller_role_{nullptr};

  void on_controller_state(const sendspin::ServerStateControllerObject &state) override;

  CallbackManager<void(const sendspin::ServerStateControllerObject &)> controller_state_callbacks_{};
#endif

#ifdef USE_SENDSPIN_MC_PLAYER
  sendspin::PlayerRoleListener *player_listener_{nullptr};
  sendspin::PlayerRoleConfig player_config_{};

  ESPPreferenceObject static_delay_pref_;
  std::optional<uint16_t> load_static_delay() override;
  bool save_static_delay(uint16_t delay_ms) override;
#endif

  ESPPreferenceObject last_played_server_pref_;

  std::unique_ptr<sendspin::SendspinClient> client_;

  CallbackManager<void(const sendspin::GroupUpdateObject &)> group_update_callbacks_{};

  std::string client_id_;
  std::string client_name_;
  uint16_t server_port_{sendspin::SendspinClientConfig::DEFAULT_SERVER_PORT};
  uint16_t control_port_{0};
  bool task_stack_in_psram_{false};
};

class SendspinMcChild : public Component, public Parented<SendspinMcHub> {
 public:
  float get_setup_priority() const override { return sendspin_mc_priority::CHILD; }
};

}  // namespace esphome::sendspin_mc

#endif  // USE_ESP32
