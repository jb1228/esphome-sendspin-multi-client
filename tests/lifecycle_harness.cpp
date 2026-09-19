// Simulated transport APIs; the methods under test are extracted from the production hub.
#include <cassert>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#define USE_MDNS_SUPPORTS_ENABLE_DISABLE
#define ESP_LOGE(...) ((void) 0)
#define LOG_STR(x) x
#define LOG_STR_LITERAL(x) x
using esp_err_t = int;
constexpr esp_err_t ESP_OK = 0;
struct mdns_txt_item_t { const char *key; const char *value; };
struct Service { std::string name; uint16_t port; };
std::vector<Service> services;
int mdns_calls = 0;

// Espressif matches a null instance against any service of the given type/protocol.
// Records are inserted at the front, so wildcard removal can remove the newest MC instance.
esp_err_t mdns_service_add(const char *name, const char *type, const char *proto, uint16_t port,
                           mdns_txt_item_t *txt, size_t count) {
  ++mdns_calls;
  assert(std::string(type) == "_sendspin" && std::string(proto) == "_tcp");
  assert(count == 1 && std::string(txt[0].key) == "path" && std::string(txt[0].value) == "/sendspin");
  for (const auto &service : services)
    if (name == nullptr || service.name == name)
      return 1;
  services.insert(services.begin(), {name ? name : "native", port});
  return ESP_OK;
}
esp_err_t mdns_service_remove_for_host(const char *name, const char *, const char *, const char *host) {
  ++mdns_calls;
  assert(host == nullptr);
  for (auto it = services.begin(); it != services.end(); ++it) {
    if (name == nullptr || it->name == name) {
      services.erase(it);
      return ESP_OK;
    }
  }
  return 1;
}
bool advertised(const char *name, uint16_t port) {
  for (const auto &s : services)
    if (s.name == name && s.port == port)
      return true;
  return false;
}
struct Client {
  bool started{false};
  bool fail_start{false};
  int starts{0};
  int stops{0};
  bool is_started() const { return started; }
  bool start() { ++starts; started = !fail_start; return started; }
  void stop() { ++stops; started = false; }
  void loop() {}
};
struct MDNS { bool ready{false}; bool is_ready() const { return ready; } };
class SendspinMcHub {
 public:
  SendspinMcHub(MDNS &mdns, const char *name, uint16_t port) : mdns_(&mdns), client_name_(name), server_port_(port) {}
  void loop();
  void set_enabled(bool enabled);
  void update_mdns_service_();
  bool status_has_error() const { return error_; }
  void status_set_error(const char *) { error_ = true; }
  std::unique_ptr<Client> client_{std::make_unique<Client>()};
  std::optional<bool> enabled_;
  MDNS *mdns_;
  bool mdns_advertised_{false};
  std::string client_name_;
  uint16_t server_port_;
  bool error_{false};
};
// PRODUCTION_METHODS

int main() {
  MDNS mdns;
  SendspinMcHub music(mdns, "music", 8931), artwork(mdns, "artwork", 8932), failed(mdns, "failed", 8933);
  // No request yet: a switch-controlled hub waits for restoration.
  artwork.loop();
  assert(artwork.client_->starts == 0);
  music.set_enabled(true);
  music.loop();
  assert(music.client_->starts == 1 && mdns_calls == 0);
  services.push_back({"native", 8928});
  mdns.ready = true;
  music.loop();
  artwork.set_enabled(false);
  artwork.loop();
  assert(advertised("music", 8931) && advertised("native", 8928) && services.size() == 2);
  artwork.set_enabled(true);
  artwork.loop();
  assert(advertised("artwork", 8932) && services.size() == 3);
  int calls = mdns_calls;
  for (int i = 0; i < 10; ++i) { music.loop(); artwork.loop(); }
  assert(mdns_calls == calls);
  music.set_enabled(false);
  music.loop();
  assert(!advertised("music", 8931) && advertised("artwork", 8932) && advertised("native", 8928));
  assert(music.client_->stops == 1 && artwork.client_->stops == 0);
  music.set_enabled(true);
  music.loop();
  assert(advertised("music", 8931) && music.client_->starts == 2);
  failed.client_->fail_start = true;
  failed.set_enabled(true);
  failed.loop();
  failed.loop();
  assert(failed.error_ && failed.client_->starts == 1 && !advertised("failed", 8933));
  // Reproduce the documented native wildcard hazard independently of MC's safe removal.
  mdns_txt_item_t txt[] = {{"path", "/sendspin"}};
  assert(mdns_service_add(nullptr, "_sendspin", "_tcp", 8928, txt, 1) != ESP_OK);
  assert(mdns_service_remove_for_host(nullptr, "_sendspin", "_tcp", nullptr) == ESP_OK);
  assert(!advertised("music", 8931) && advertised("native", 8928));
}
