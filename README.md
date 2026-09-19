# ESPHome Sendspin Multi-Client

`sendspin_mc` is a multi-instance adaptation of ESPHome's core `sendspin`
component. It can run by itself or alongside the native component on the same
ESP32 device.

The implementation is based on ESPHome `dev` commit
[`8bcb500`](https://github.com/esphome/esphome/tree/8bcb5004da8af416f11028bf4609f2c78ca104e5/esphome/components/sendspin)
and includes the same hub, switch action, media source, controller media player,
artwork, numeric sensors, and text sensors.

## Differences from ESPHome's Core Sendspin Component

- The domain, C++ namespace, actions, and parent key use `sendspin_mc` so the
  component does not replace or collide with core `sendspin`.
- `sendspin_mc` accepts multiple hub entries. Every hub requires a unique
  `client_id`, `client_name`, `server_port`, and `control_port`.
- `client_id` must be non-empty and cannot contain `/`; `client_name` must fit
  one DNS-SD label (63 UTF-8 bytes) and is compared case-insensitively for mDNS
  uniqueness.
- Child platforms select their hub with `sendspin_mc_id`. ESPHome can infer the
  parent when only one hub is configured.
- Roles, preferences, media-source URIs, WebSocket servers, and mDNS services
  are isolated per hub. Shared `sendspin-cpp` build flags are reconciled with
  the official component when both are present.

No additional playback, metadata, or controller behavior is added beyond what
is needed for multiple clients.

MC and native Sendspin share one `sendspin/sendspin-cpp` library and must
reference the same version. Use `sendspin_cpp_ref` to match the version used by
native Sendspin. All MC hubs must agree on that
version; when native Sendspin is present, match its dependency version as well.
The MC-hub agreement is validated; agreement with native is currently the
configuration author's responsibility.

### Implementation differences

- Each client registers its own named mDNS service.
- Hubs initialize after mDNS, followed by their child components.
- Shared library role flags account for both MC and native clients.

## Installation

```yaml
external_components:
  - source: github://jb1228/esphome-sendspin-multi-client@main
    components: [sendspin_mc]
```

## Configuration

```yaml
sendspin_mc:
  - id: sendspin_music
    client_id: "${name}-music"
    client_name: "${friendly_name} Music"
    server_port: 8931
    control_port: 32771
    task_stack_in_psram: true

  - id: sendspin_notifications
    client_id: "${name}-notifications"
    client_name: "${friendly_name} Notifications"
    server_port: 8932
    control_port: 32772
    task_stack_in_psram: true
```

All other options belong to the same child platforms as core Sendspin:

- `media_source: { platform: sendspin_mc }` supports buffer size, sample rate,
  static/fixed delay, decode memory, and PSRAM task stacks.
- `media_player: { platform: sendspin_mc }` exposes the controller role.
- Numeric sensor types are `track_progress`, `track_duration`, `year`, and
  `track`.
- Text sensor types are `title`, `artist`, `album`, and `album_artist`.
- Actions are `sendspin_mc.switch`,
  `sendspin_mc.media_source.enable_static_delay_adjustment`, and
  `sendspin_mc.media_source.disable_static_delay_adjustment`.

Each media source owns the URI prefix
`sendspin_mc://<client_id>/`. The current inbound stream uses `current`; a
different suffix retains core Sendspin's remote-server connection behavior.

See [sample_package.yaml](sample_package.yaml) for a reusable package that can
be included multiple times with different `sendspin_instance` values.

When core `sendspin` is also configured, do not use its fixed server port 8928
or HTTP control port 32769 for a `sendspin_mc` hub. Configuration validation
rejects those collisions.


### Important Note: 
> The native Sendspin currently adds and removes `_sendspin._tcp` without an instance name. Espressif treats those lookups as matching any instance, so native registration can collide with MC, and disabling native can remove an MC advertisement. Unique names and ports do not prevent this.

To work around this when using this alongside the native component, I am currently keeping the `sendspin_mc` disabled until the native is enabled, which seems to be working for the time being:

``` yaml
switch:

  - platform: sendspin_mc
    id: switch_sendspin_mc_enabled
    sendspin_mc_id: ${sendspin_mc_hub_id}
    name: "Sendspin Multi-Client Enabled"
    restore_mode: ALWAYS_OFF

    # Native ESPHome Sendspin Component:
  - platform: sendspin 
    id: switch_sendspin_native_enabled
    sendspin_id: ${sendspin_hub_id}
    name: "Sendspin Native Enabled"
    restore_mode: ALWAYS_ON
    on_turn_on:
      - delay: 1s
      - switch.turn_on: switch_sendspin_mc_enabled
```
