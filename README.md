# ESPHome Sendspin Multi-Client

`sendspin_mc` is a multi-instance adaptation of ESPHome's core `sendspin`
component. It can run by itself or alongside the official component on the same
ESP32 device.

The implementation is based on ESPHome `dev` commit
[`e50fae3`](https://github.com/esphome/esphome/tree/e50fae3f4693d01031d687e911d6749e9dbec338/esphome/components/sendspin)
and includes the same hub, switch action, media source, controller media player,
numeric sensors, and text sensors.

## Differences from ESPHome core

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

## Installation

```yaml
external_components:
  - source: github://jb1228/esphome-sendspin-multi-client@main
    components: [sendspin_mc]
```

The component declares the same `sendspin/sendspin-cpp` dependency as ESPHome
core; no `esp32.framework.components` entry is required.

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
