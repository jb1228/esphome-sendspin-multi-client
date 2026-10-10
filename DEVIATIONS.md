# Temporary implementation deviations

Internal maintenance notes for the workarounds marked in code. Necessary
multi-client adaptations and the shared-library version setting are covered by
AGENTS.md and are not temporary deviations.

Reviewed against native ESPHome `dev` commit
[`a4a09043ec`](https://github.com/esphome/esphome/tree/a4a09043ec1c1b5dd1f35c785125d751d56f2b43/esphome/components/sendspin).
Revisit these deviations on subsequent updates.

1. **Custom mDNS registration** —
   [`update_mdns_service_()`](sendspin_mc/sendspin_mc_hub.cpp) calls Espressif's
   API directly to advertise each client's name and port. Native uses ESPHome's
   managed service registration and enable/disable lifecycle. The custom path
   supplies independent instances that the native integration does not manage.
   Replace it when native mDNS can register, enable, disable, and remove each
   instance independently. The coexistence collision identified after
   [#19325](https://github.com/esphome/esphome/pull/19325),
   [#19326](https://github.com/esphome/esphome/pull/19326), and
   [#19361](https://github.com/esphome/esphome/pull/19361) remains unresolved.
2. **Late shared build-flag reconciliation** —
   [`_finalize_sendspin_sdkconfig()`](sendspin_mc/__init__.py) runs after native
   code generation to preserve library roles and Opus required by MC. Native configures
   shared flags from its own requirements, which may disable roles or codecs needed
   by another client. Remove or simplify this final override when shared/native
   code generation aggregates all clients' role requirements.
3. **Implicit-parent configuration merging** —
   [`_get_codegen_data()`](sendspin_mc/__init__.py) merges role, pairing-display, and switch requests collected
   before an omitted parent ID is resolved into the single configured hub.
   Native has one configuration bucket and needs no such merge. MC needs it to
   retain implicit-parent behavior while storing configuration per hub. Remove
   or simplify it when validation can associate those requests directly with
   their resolved hub.
4. **Artwork slot registration after ID resolution** —
   [`FINAL_VALIDATE_SCHEMA`](sendspin_mc/image/__init__.py) assigns artwork slots
   after parent IDs resolve. Native registers preferences during ordinary schema
   validation. MC needs one counter per resolved hub for mixed explicit and implicit
   references. Simplify this when ordinary validation can reliably resolve the owner.

The former custom setup-ordering deviation no longer applies: MC uses native's
hub/child priorities and waits for mDNS readiness in its loop.

## Intentional parity gap

Native API pairing-token retrieval is intentionally omitted for MC. It supports
automated pairing by handing a server the client's long-lived pairing token;
static and dynamic code pairing do not depend on it. The native
request has no hub selector, is compiled only for `USE_SENDSPIN`, and retrieves
its token from `sendspin_::global_sendspin_hub`. Each MC hub exposes the same
C++ token getter. Extending the standard endpoint requires core changes, which
are outside the approved scope; custom API actions are also intentionally
excluded. Do not advertise the native token capability for MC. Revisit this gap
if native ESPHome adds an API that can address individual clients.
