# Validation fixtures

The `test-*.esp32-idf.yaml` files are expected to pass ESPHome configuration
validation and C++ generation. The `invalid-*.esp32-idf.yaml` files are expected
to fail with their required-field, identity, mDNS-name, URI, or port-collision
error, or a pairing-code, pairing-method, switch-owner, or unpaired-setting error.

The fixtures cover every upstream Sendspin child platform and action, implicit
single-hub parent selection, mixed per-hub roles across three clients, and
coexistence with core `sendspin`. Pairing fixtures cover static and dynamic
methods on different hubs, callbacks/actions, typed switches, and implicit
parents without requiring the metadata role.

Run `python3 tests/verify.py` to validate the configuration fixtures and assert
the generated three-hub role matrix, instance-specific URIs and preferences, and per-hub mDNS
registration and pairing wiring. These checks generate C++ without compiling
firmware.

Run `python3 tests/test_lifecycle.py` for the host simulation of per-client
startup, switch settings, pairing-window actions, and discovery ownership.
