#!/usr/bin/env python3
"""Run configuration and generated-code regression checks for sendspin_mc."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
BUILD = TESTS / ".esphome" / "build" / "sendspin-mc-test"


def run_esphome(*args: str, expect_success: bool = True) -> str:
    result = subprocess.run(
        ["esphome", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if expect_success and result.returncode != 0:
        raise AssertionError(f"ESPHome {' '.join(args)} failed:\n{output}")
    if not expect_success and result.returncode == 0:
        raise AssertionError(f"ESPHome {' '.join(args)} unexpectedly passed")
    return output


def assert_contains(text: str, *needles: str) -> None:
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"Expected generated output to contain: {needle}")


def verify_valid_configs() -> None:
    for filename in (
        "test-full.esp32-idf.yaml",
        "test-implicit-parent.esp32-idf.yaml",
        "test-multi.esp32-idf.yaml",
        "test-coexist.esp32-idf.yaml",
    ):
        run_esphome("config", str(TESTS / filename))


def verify_invalid_configs() -> None:
    expected_errors = {
        "invalid-client-id-uri.esp32-idf.yaml": "client_id must not contain '/'",
        "invalid-core-mdns-name.esp32-idf.yaml": "conflicts with the official sendspin mDNS instance",
        "invalid-core-port.esp32-idf.yaml": "conflicts with the official sendspin server",
        "invalid-duplicate-client-id.esp32-idf.yaml": "client ID must be unique",
        "invalid-duplicate-client-name.esp32-idf.yaml": "client name must be unique",
        "invalid-duplicate-ports.esp32-idf.yaml": "conflicts with sendspin_mc hub",
        "invalid-mdns-name.esp32-idf.yaml": "client_name must be at most 63 UTF-8 bytes",
        "invalid-missing-required.esp32-idf.yaml": "required key not provided",
    }
    for filename, expected_error in expected_errors.items():
        output = run_esphome("config", str(TESTS / filename), expect_success=False)
        assert_contains(output, expected_error)


def verify_multi_codegen() -> None:
    run_esphome("compile", "--only-generate", str(TESTS / "test-multi.esp32-idf.yaml"))
    main_cpp = (BUILD / "src" / "main.cpp").read_text()
    defines = (BUILD / "src" / "esphome" / "core" / "defines.h").read_text()
    hub_header = (ROOT / "sendspin_mc" / "sendspin_mc_hub.h").read_text()
    hub_source = (ROOT / "sendspin_mc" / "sendspin_mc_hub.cpp").read_text()

    assert_contains(
        main_cpp,
        'sendspin_mc_player->set_client_id("sendspin-mc-player")',
        'sendspin_mc_metadata->set_client_id("sendspin-mc-metadata")',
        'sendspin_mc_controller->set_client_id("sendspin-mc-controller")',
        "sendspin_mc_player->set_server_port(8931)",
        "sendspin_mc_metadata->set_server_port(8932)",
        "sendspin_mc_controller->set_server_port(8933)",
        "sendspin_mc_player->set_controller_support(true)",
        "sendspin_mc_player->set_metadata_support(false)",
        "sendspin_mc_player->set_player_support(true)",
        "sendspin_mc_metadata->set_controller_support(false)",
        "sendspin_mc_metadata->set_metadata_support(true)",
        "sendspin_mc_metadata->set_player_support(false)",
        "sendspin_mc_controller->set_controller_support(true)",
        "sendspin_mc_controller->set_metadata_support(false)",
        "sendspin_mc_controller->set_player_support(false)",
    )
    assert_contains(
        defines,
        "#define USE_SENDSPIN_MC_CONTROLLER true",
        "#define USE_SENDSPIN_MC_METADATA true",
        "#define USE_SENDSPIN_MC_PLAYER true",
    )
    assert_contains(
        hub_header,
        'return "sendspin_mc://" + this->client_id_ + "/" + target',
    )
    assert_contains(
        hub_source,
        'fnv1a_hash("sendspin_mc_last_played_" + this->client_id_)',
        'fnv1a_hash("sendspin_mc_static_delay_" + this->client_id_)',
        'mdns_service_add(this->client_name_.c_str(), "_sendspin", "_tcp", this->server_port_',
        '{(char *) "path", (char *) SENDSPIN_PATH}',
    )


def main() -> None:
    verify_valid_configs()
    verify_invalid_configs()
    verify_multi_codegen()
    print("sendspin_mc validation passed")


if __name__ == "__main__":
    main()
