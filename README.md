# ESPHome Sendspin Multi-Client

`sendspin_mc` is a multi-instance adaptation of ESPHome's core `sendspin`
component. It can run by itself or alongside the native component on the same
ESP32 device.

The implementation targets ESPHome `dev` commit
[`a4a09043ec`](https://github.com/esphome/esphome/tree/a4a09043ec1c1b5dd1f35c785125d751d56f2b43/esphome/components/sendspin)
and sendspin-cpp `0.9.3`. It includes the hub, typed switches, controller and
pairing-window actions, media source, controller media player, artwork, numeric
sensors, metadata text sensors, and static/dynamic pairing. Pairing configuration
and callbacks belong to each hub.

## Important limitations

- **No automated pairing through the native API.** MC clients cannot supply
  pairing tokens through ESPHome's standard Sendspin API endpoint, which
  addresses only the native hub. Pair MC clients using static or dynamic codes,
  or allow unpaired playback. Custom token-retrieval API actions are not provided.
- **Native coexistence has an mDNS discovery limitation.** Native Sendspin
  addresses `_sendspin._tcp` services without an instance name. Its registration
  can collide with MC, and disabling native can remove an MC advertisement.
  Unique client names and ports do not prevent this. See the
  [startup workaround](#native-coexistence-workaround) below; it does not fix
  native's removal behavior.
- **MC and native must use the same sendspin-cpp version.** They share one
  library. Set `sendspin_cpp_ref` to match native's dependency when both are used.
  Agreement between MC hubs is validated; agreement with native is the
  configuration author's responsibility.

ESP-IDF is required. Connections use the Sendspin 1.0.0-rc1 protocol; Music
Assistant must support that protocol (2.11.0b4 or newer). Unpaired access is
enabled by default, so a compatible server can play without pairing. Artwork must
use JPEG or PNG, and media-source codecs must include FLAC or PCM.

## Differences from ESPHome's Core Sendspin Component

- The domain, C++ namespace, actions, and parent key use `sendspin_mc` so the
  component does not replace or collide with core `sendspin`.
- `sendspin_mc` accepts multiple hub entries. Every hub requires a unique
  `client_id`, `client_name`, `server_port`, and `control_port`.
- `client_id` must be non-empty and cannot contain `/`; `client_name` must fit
  one DNS-SD label (63 UTF-8 bytes) and is compared case-insensitively for mDNS
  uniqueness.
- The configured `client_id` is a stable local key for preferences and media-source
  URIs. The protocol client ID comes from each hub's independently persisted
  keypair. Keep the local key unchanged to preserve that identity across updates.
- Child platforms select their hub with `sendspin_mc_id`. ESPHome can infer the
  parent when only one hub is configured.
- Roles, preferences, media-source URIs, WebSocket servers, and mDNS services
  are isolated per hub. Each client registers its own named mDNS service.
- Hubs use native setup ordering and advertise from their loop after mDNS is ready.
- Shared `sendspin-cpp` build flags account for both MC and native clients when
  both components are present.

No additional playback, metadata, or controller behavior is added beyond what
is needed for multiple clients.

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
- Text sensor types are `title`, `artist`, `album`, `album_artist`, and `pairing_code`.
- Switches require `type: enabled` or `type: unpaired_access`; at most one of
  each type can control a hub. Existing enable switches must add `type: enabled`.
- Actions are `sendspin_mc.switch`, `sendspin_mc.confirm_pairing_window`,
  `sendspin_mc.cancel_pairing_window`, `sendspin_mc.image.transition_finished`,
  `sendspin_mc.media_source.enable_static_delay_adjustment`, and
  `sendspin_mc.media_source.disable_static_delay_adjustment`.

### Pairing

Each hub accepts an eight-digit quoted `static_pairing_code`, or advertises
numeric dynamic codes when it has an `on_display_pairing_code` automation or a
`pairing_code` text sensor. Static and dynamic codes cannot be configured on the
same hub. For example, these child entities enable dynamic pairing on the music
hub:

```yaml
text_sensor:
  - platform: sendspin_mc
    sendspin_mc_id: sendspin_music
    type: pairing_code
    name: Music Pairing Code

switch:
  - platform: sendspin_mc
    sendspin_mc_id: sendspin_music
    type: unpaired_access
    name: Music Unpaired Access
    restore_mode: ALWAYS_OFF
```

The sensor clears when the library clears the code. The hub also accepts
`on_open_pairing_window`, `on_close_pairing_window`, `on_clear_pairing_code`,
`on_pairing_succeeded` (`server_id`), and `on_pairing_failed` (`server_id`, `reason`)
automations. `on_display_pairing_code` receives `code`.

Without an unpaired-access switch, set `unpaired_access: false` on the hub to
require pairing. With a switch, use its `restore_mode` instead of setting the
hub option. The client's first start waits for both switches to restore their
settings when configured.

Each media source owns the URI prefix
`sendspin_mc://<client_id>/`. The current inbound stream uses `current`; a
different suffix retains core Sendspin's remote-server connection behavior.

See [sample_package.yaml](sample_package.yaml) for a reusable package that can
be included multiple times with different `sendspin_instance` values.

When core `sendspin` is also configured, do not use its fixed server port 8928
or HTTP control port 32769 for a `sendspin_mc` hub. Configuration validation
rejects those collisions.

### Native coexistence workaround

The following startup workaround has worked in this setup: keep MC disabled
until native Sendspin is enabled. It orders registration but does not prevent
native from removing an MC advertisement if native is later disabled.

``` yaml
switch:

  - platform: sendspin_mc
    type: enabled
    id: switch_sendspin_mc_enabled
    sendspin_mc_id: ${sendspin_mc_hub_id}
    name: "Sendspin Multi-Client Enabled"
    restore_mode: ALWAYS_OFF

    # Native ESPHome Sendspin Component:
  - platform: sendspin 
    type: enabled
    id: switch_sendspin_native_enabled
    sendspin_id: ${sendspin_hub_id}
    name: "Sendspin Native Enabled"
    restore_mode: ALWAYS_ON
    on_turn_on:
      - delay: 1s
      - switch.turn_on: switch_sendspin_mc_enabled
```
