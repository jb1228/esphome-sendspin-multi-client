#include "sendspin_mc_hub.h"

#ifdef USE_ESP32

#include "esphome/components/network/util.h"
#ifdef USE_WIFI
#include "esphome/components/wifi/wifi_component.h"
#endif

#include "esphome/core/application.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"
#include "esphome/core/version.h"

#include <esp_log.h>
#include <mdns.h>

namespace esphome::sendspin_mc {

static const char *const TAG = "sendspin_mc.hub";
static constexpr const char *SENDSPIN_PATH = "/sendspin";

void SendspinMcHub::setup() {
  auto config = this->build_client_config_();
  this->client_ = std::make_unique<sendspin::SendspinClient>(std::move(config));

  this->last_played_server_pref_ = global_preferences->make_preference<LastPlayedServerPref>(
      fnv1a_hash("sendspin_mc_last_played_" + this->client_id_));
#ifdef USE_SENDSPIN_MC_PLAYER
  this->static_delay_pref_ =
      global_preferences->make_preference<StaticDelayPref>(fnv1a_hash("sendspin_mc_static_delay_" + this->client_id_));
#endif

  this->client_->set_listener(this);
  this->client_->set_network_provider(this);
  this->client_->set_persistence_provider(this);

#ifdef USE_SENDSPIN_MC_CONTROLLER
  this->controller_role_ = &this->client_->add_controller();
  this->controller_role_->set_listener(this);
#endif

#ifdef USE_SENDSPIN_MC_PLAYER
  this->client_->add_player(this->player_config_).set_listener(this->player_listener_);
#endif

  if (!this->client_->start_server()) {
    ESP_LOGE(TAG, "Failed to start Sendspin MC server");
    this->mark_failed();
    return;
  }

  this->register_mdns_service_();
}

void SendspinMcHub::loop() { this->client_->loop(); }

void SendspinMcHub::dump_config() {
  ESP_LOGCONFIG(TAG,
                "Sendspin MC Hub:\n"
                "  Client ID: %s\n"
                "  Client Name: %s\n"
                "  Server Port: %u\n"
                "  Control Port: %u\n"
                "  Task stack in PSRAM: %s",
                this->client_id_.c_str(), this->client_name_.c_str(), this->server_port_, this->control_port_,
                YESNO(this->task_stack_in_psram_));
}

void SendspinMcHub::connect_to_server(const std::string &url) {
  if (this->is_ready()) {
    this->client_->connect_to(url);
  }
}

void SendspinMcHub::disconnect_from_server(sendspin::SendspinGoodbyeReason reason) {
  if (this->is_ready()) {
    this->client_->disconnect(reason);
  }
}

void SendspinMcHub::update_state(sendspin::SendspinClientState state) {
  if (this->is_ready()) {
    this->client_->update_state(state);
  }
}

sendspin::SendspinClientConfig SendspinMcHub::build_client_config_() {
  sendspin::SendspinClientConfig config;

  config.client_id = this->client_id_;
  config.name = this->client_name_;
  config.product_name = App.get_name();
  config.manufacturer = "ESPHome";
  config.software_version = ESPHOME_VERSION;
  config.server_port = this->server_port_;
  config.httpd_ctrl_port = this->control_port_;
  config.server_max_connections = 2;
  config.httpd_psram_stack = this->task_stack_in_psram_;

  return config;
}

void SendspinMcHub::register_mdns_service_() {
  mdns_txt_item_t txt_records[] = {
      {(char *) "path", (char *) SENDSPIN_PATH},
      {(char *) "name", (char *) this->client_name_.c_str()},
      {(char *) "client_id", (char *) this->client_id_.c_str()},
  };
  esp_err_t err = mdns_service_add(this->client_name_.c_str(), "_sendspin", "_tcp", this->server_port_, txt_records, 3);
  if (err != ESP_OK) {
    ESP_LOGW(TAG, "Failed to register mDNS service: %s", esp_err_to_name(err));
  } else {
    ESP_LOGI(TAG, "Registered mDNS service: %s._sendspin._tcp on port %u", this->client_name_.c_str(),
             this->server_port_);
  }
}

void SendspinMcHub::on_group_update(const sendspin::GroupUpdateObject &group) {
  this->group_update_callbacks_.call(group);
}

void SendspinMcHub::on_request_high_performance() {
#ifdef USE_WIFI
  if (wifi::global_wifi_component != nullptr) {
    wifi::global_wifi_component->request_high_performance();
  }
#endif
}

void SendspinMcHub::on_release_high_performance() {
#ifdef USE_WIFI
  if (wifi::global_wifi_component != nullptr) {
    wifi::global_wifi_component->release_high_performance();
  }
#endif
}

bool SendspinMcHub::is_network_ready() { return network::is_connected(); }

bool SendspinMcHub::save_last_server_hash(uint32_t hash) {
  LastPlayedServerPref pref{.server_id_hash = hash};
  bool ok = this->last_played_server_pref_.save(&pref);
  if (ok) {
    ESP_LOGD(TAG, "Persisted last played server hash: 0x%08" PRIX32, hash);
  } else {
    ESP_LOGW(TAG, "Failed to persist last played server hash");
  }
  return ok;
}

std::optional<uint32_t> SendspinMcHub::load_last_server_hash() {
  LastPlayedServerPref pref{};
  if (this->last_played_server_pref_.load(&pref)) {
    ESP_LOGI(TAG, "Loaded last played server hash: 0x%08" PRIX32, pref.server_id_hash);
    return pref.server_id_hash;
  }
  return std::nullopt;
}

#ifdef USE_SENDSPIN_MC_CONTROLLER
void SendspinMcHub::send_client_command(sendspin::SendspinControllerCommand command, std::optional<uint8_t> volume,
                                        std::optional<bool> mute) {
  if (this->is_ready()) {
    this->controller_role_->send_command(command, volume, mute);
  }
}

void SendspinMcHub::on_controller_state(const sendspin::ServerStateControllerObject &state) {
  this->controller_state_callbacks_.call(state);
}
#endif

#ifdef USE_SENDSPIN_MC_PLAYER
sendspin::PlayerRole *SendspinMcHub::get_player_role() {
  if (this->is_ready()) {
    return this->client_->player();
  }
  return nullptr;
}

bool SendspinMcHub::save_static_delay(uint16_t delay_ms) {
  StaticDelayPref pref{.delay_ms = delay_ms};
  bool ok = this->static_delay_pref_.save(&pref);
  if (ok) {
    ESP_LOGD(TAG, "Persisted static delay: %u ms", delay_ms);
  } else {
    ESP_LOGW(TAG, "Failed to persist static delay");
  }
  return ok;
}

std::optional<uint16_t> SendspinMcHub::load_static_delay() {
  StaticDelayPref pref{};
  if (this->static_delay_pref_.load(&pref)) {
    ESP_LOGI(TAG, "Loaded static delay: %u ms", pref.delay_ms);
    return pref.delay_ms;
  }
  return std::nullopt;
}
#endif

}  // namespace esphome::sendspin_mc

#endif  // USE_ESP32
