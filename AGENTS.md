# Instructions for sendspin_mc

These instructions apply to this directory and all descendants.

## Primary goal

Allow multiple independent Sendspin clients to exist on the same ESPHome
device, including coexistence with ESPHome's native `sendspin` component.
Keep client identities, ports, discovery records, runtime state, and persisted
preferences isolated wherever necessary to achieve this goal.

If native ESPHome Sendspin gains multi-client support, this component will no
longer be necessary. Prefer migration to native support over maintaining a
separate implementation.

## Assumed multi-client adaptations

The following are permanent design requirements for this component and do not
need temporary-deviation markers:

- Separate component domain, namespace, classes, defines, actions, and parent
  keys to coexist with native Sendspin.
- Multiple hubs with independent client IDs, names, server ports, and control
  ports, including validation to prevent collisions.
- Per-hub role configuration and runtime guards to isolate each client's roles.
- Client-specific preference keys for independent persisted state.
- Instance-specific media-source URIs to route requests to the correct client.
- Configurable `sendspin_cpp_ref` to match the library version used by native
  Sendspin. Both components share one library and cannot reference different
  versions; this compatibility setting is not a temporary deviation.

Preserve these adaptations while following native implementation patterns as
closely as possible. Their necessity does not exempt implementation workarounds
from the temporary-deviation requirements below.

## Native ESPHome parity

- Treat the currently installed ESPHome `dev` branch's `sendspin` component as
  the reference implementation. Assume updates target ESPHome `dev`, not the
  latest stable release or the historical baseline recorded in README.md.
- Locate and inspect the actual ESPHome installation and its native source
  before updating this component. Record the reference commit when updating
  the documented baseline; do not assume a previously recorded commit is still
  current.
- Maintain feature and code parity with native Sendspin. Follow its schemas,
  defaults, validation, lifecycle, platforms, actions, dependency versions,
  and integration processes as closely as possible.
- Do not deviate from native code or processes unless absolutely necessary to
  support multiple clients or coexistence with native Sendspin. Prefer the
  smallest adaptation of native code over a separate implementation.
- Avoid unrelated features, refactors, or behavioral changes. Where native
  behavior can be reused with instance-specific identifiers and ownership,
  preserve the native implementation.

## Temporary deviations

- Beyond the assumed multi-client adaptations above, explicitly mark required
  implementation deviations and workarounds as temporary. This includes custom
  code-generation ordering, initialization, discovery, and other integration
  processes that depart from native behavior.
- Missing native features and behavior are unimplemented parity work, not
  temporary deviations. Track them separately without temporary-deviation
  markers.
- Add a concise `TEMPORARY DEVIATION` comment near the affected code and document
  the difference in [DEVIATIONS.md](DEVIATIONS.md). Each entry must explain
  the relevant requirement, the native behavior being changed, why the deviation
  is currently necessary, and what would allow it to be reduced or removed.
  Include an upstream issue or PR reference when one exists.
- On every subsequent component update, revisit existing temporary deviations
  in DEVIATIONS.md against the current native `dev` implementation. Do not carry
  a workaround forward merely because it already exists.
- Remove deviations that are no longer needed and revise remaining ones to
  restore as much native code and feature parity as possible. If a deviation
  must remain, document why it is still necessary and the reference commit
  against which it was reviewed.
- Keep the README's baseline and feature list, and the detailed notes in
  DEVIATIONS.md, consistent with the implementation. Clearly identify any
  remaining parity gaps rather than claiming parity that has not been checked.
- Keep internal instructions, temporary labels, review history, and removal
  criteria out of README.md. Its implementation differences should be a short,
  descriptive list for users; maintenance details belong in DEVIATIONS.md.

## Validation and reporting

For functional updates, use checks appropriate to the change to cover both
multiple `sendspin_mc` clients and coexistence with native `sendspin`. Verify
that operations on one client do not unintentionally affect another. Follow
any validation limits specified by the user, and distinguish configuration
validation, compilation, and live device testing in reports.
