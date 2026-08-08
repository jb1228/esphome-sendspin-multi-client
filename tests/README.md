# Validation fixtures

The `test-*.esp32-idf.yaml` files are expected to pass ESPHome configuration
validation and C++ generation. The `invalid-*.esp32-idf.yaml` files are expected
to fail with their required-field, identity, mDNS-name, URI, or port-collision
error.

The fixtures cover every upstream Sendspin child platform and action, implicit
single-hub parent selection, mixed per-hub roles across three clients, and
coexistence with core `sendspin`.

Run `python3 tests/verify.py` to validate all fixtures and assert the generated
three-hub role matrix, instance-specific URIs and preferences, and per-hub mDNS
registration.
