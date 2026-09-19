# Temporary implementation deviations

Internal maintenance notes for the workarounds marked in code. Necessary
multi-client adaptations and the shared-library version setting are covered by
AGENTS.md and are not temporary deviations.

Reviewed against native ESPHome `dev` commit
[`f94661561d`](https://github.com/esphome/esphome/tree/f94661561df60e2c68593f757d340ee0b9c770fd/esphome/components/sendspin).
This is a review reference, not a claim that the implementation has been
updated to that commit. Revisit all four deviations on subsequent updates.

1. **Custom mDNS registration** —
   [`register_mdns_service_()`](sendspin_mc/sendspin_mc_hub.cpp) calls Espressif's
   API directly to advertise each client's name and port. Native uses ESPHome's
   managed service registration and enable/disable lifecycle. The custom path
   supplies independent instances that the native integration does not manage.
   Replace it when native mDNS can register, enable, disable, and remove each
   instance independently. The coexistence collision identified after
   [#19325](https://github.com/esphome/esphome/pull/19325),
   [#19326](https://github.com/esphome/esphome/pull/19326), and
   [#19361](https://github.com/esphome/esphome/pull/19361) remains unresolved.
2. **Custom setup ordering** —
   [`sendspin_mc_priority`](sendspin_mc/sendspin_mc_hub.h) initializes hubs after
   ESPHome's mDNS component so direct registration can succeed; children follow
   their hub. Native's hub initializes before mDNS and updates advertisement
   from its loop. Revisit this ordering with the discovery workaround and
   restore native ordering when registration no longer requires the delay.
3. **Late shared build-flag reconciliation** —
   [`_finalize_sendspin_sdkconfig()`](sendspin_mc/__init__.py) runs after native
   code generation to preserve library roles required by MC. Native configures
   shared role flags from its own requirements, which may disable roles needed
   by another client. Remove or simplify this final override when shared/native
   code generation aggregates all clients' role requirements.
4. **Implicit-parent configuration merging** —
   [`_get_codegen_data()`](sendspin_mc/__init__.py) merges role requests collected
   before an omitted parent ID is resolved into the single configured hub.
   Native has one configuration bucket and needs no such merge. MC needs it to
   retain implicit-parent behavior while storing configuration per hub. Remove
   or simplify it when validation can associate those requests directly with
   their resolved hub.

Native features and behavior that have not yet been implemented in MC are
parity work, not temporary implementation deviations.
