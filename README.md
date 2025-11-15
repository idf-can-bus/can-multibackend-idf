# can-multibackend-idf

Unified CAN-bus Interface and Example Suite for ESP-IDF
========================================================

This project provides a modular, unified interface for CAN bus communication on ESP-IDF platforms (ESP32, ESP32-S3, ESP32-C3, ESP32-C6), supporting multiple hardware backends through a common abstraction layer. It is designed for easy switching between different CAN controllers and for rapid prototyping or testing of CAN networks.

## Architecture Overview

This integration project combines three independent CAN libraries under a unified interface:

### Core Libraries

1. **[twai-idf-can](https://github.com/idf-can-bus/twai-idf-can)** — High-level wrapper for ESP32's built-in TWAI (CAN) controller with automatic error recovery
   - Direct support for ESP32's native CAN peripheral
   - Simplified configuration and initialization
   - Automatic bus-off recovery

2. **[mcp2515-esp32-idf](https://github.com/Microver-Electronics/mcp2515-esp32-idf)** — External library for single MCP2515 CAN controller via SPI
   - Low-level driver for MCP2515 chip
   - Single-device operation
   - Third-party library by Microver-Electronics

3. **[mcp25xxx-multi-idf-can](https://github.com/idf-can-bus/mcp25xxx-multi-idf-can)** — Multi-device adapter for MCP25xxx family (MCP2515, MCP25625, etc.)
   - Supports multiple MCP25xxx controllers simultaneously
   - Built upon and extends mcp2515-esp32-idf
   - Unified multi-device API

### Shared Components

- **[examples-utils-idf-can](https://github.com/idf-can-bus/examples-utils-idf-can)** — Common utility functions shared across all examples
  - Message formatting and display
  - Timing and synchronization helpers
  - Reusable across all backend types

All repositories are maintained under the **[idf-can-bus](https://github.com/idf-can-bus)** organization on GitHub.

## Features

- **Unified API:** Switch between CAN backends via Kconfig without code changes
- **Backend Abstraction:** `can_dispatch` component provides consistent `can_twai_*` interface for single-device examples
- **Multiple Examples:** Send, receive (polling), receive (interrupt) for both single and multi-device scenarios
- **Easy Configuration:** Select backend and example via `idf.py menuconfig`
- **Development Tools:** Python-based flash manager with GUI for multi-device workflows
- **Automatic Testing:** `test_compilation.py` validates all backend/example combinations

## Supported Hardware Configurations

| Configuration | Backend Library | Hardware | Use Case |
|---------------|----------------|----------|----------|
| **TWAI** | [twai-idf-can](https://github.com/idf-can-bus/twai-idf-can) | ESP32 built-in CAN + SN65HVD230 transceiver | Native CAN controller, best performance |
| **MCP2515 Single** | [mcp2515-esp32-idf](https://github.com/Microver-Electronics/mcp2515-esp32-idf) (via `can_dispatch`) | One MCP2515 module via SPI | External CAN controller, single device |
| **MCP25xxx Multi** | [mcp25xxx-multi-idf-can](https://github.com/idf-can-bus/mcp25xxx-multi-idf-can) | Multiple MCP2515/MCP25625 modules via SPI | Multiple independent CAN buses |

## Example Applications

This project provides **12 example configurations** combining 3 example types with 4 backend configurations (**MCP25xxx Multi** is used twice:  for both single-device and multiple-device examples.).

Examples are organized by device count (single/multi) and maintained in their respective component repositories:

| Library/HW | | **Single Device** | | | **Multi Device** | |
|------------|---------|-------------------|---------|---------|------------------|---------|
| | **send** | **receive_poll** | **receive_interrupt** | **send** | **receive_poll** | **receive_interrupt** |
| **TWAI**<br>(ESP32 built-in CAN) | ✅ | ✅ | ✅ | — | — | — |
| **MCP2515 Single**<br>(External via SPI) | ✅ | ✅ | ✅ | — | — | — |
| **MCP25xxx Multi**<br>(Multiple devices via SPI) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Notes:**
- **Single examples** use `can_twai_*` API (unified via `can_dispatch`)
- **Multi examples** use `canif_*` API (direct from mcp25xxx-multi-idf-can)
- **MCP25xxx Multi (single mode)** uses the multi-device library with `device_count = 1`
- All examples share utilities from `examples-utils-idf-can`

### Example Locations

**Single Device (TWAI & MCP2515):**
- Source: [`components/twai-idf-can/examples/`](https://github.com/idf-can-bus/twai-idf-can/tree/master/examples)
- API: `can_twai_*` functions
- Backends: Selectable via Kconfig (TWAI or MCP2515 single)

**Multi Device (MCP25xxx):**
- Source: [`components/mcp25xxx-multi-idf-can/examples/`](https://github.com/idf-can-bus/mcp25xxx-multi-idf-can/tree/master/examples)
- API: `canif_*` functions
- Backend: Multiple MCP25xxx controllers

For detailed usage and API documentation, see the respective library repositories linked above.

For local navigation, see [`examples/README.md`](examples/README.md)

## Hardware Wiring

### Typical MCP2515 Setup
![Single MCP2515 wiring](doc/single_setup.wiring.drawio.png)

**Important notes:**
- **CAN bus termination:** The general recommendation is to place one 120-ohm termination resistor at each end of a long CAN bus. However, the author's experience with short experimental setups shows that using only one 120-ohm resistor for the entire bus often works better. Hardware details are not covered by these libraries.
- Custom GPIO assignments are configurable (see example configuration files)
- Either SPI2_HOST or SPI3_HOST can be used on ESP32
- For TWAI wiring, see [twai-idf-can documentation](https://github.com/idf-can-bus/twai-idf-can)

## Building and Flashing

### Prerequisites

Before building, ensure ESP-IDF is properly installed and activated:

```sh
# Activate ESP-IDF environment
. $HOME/esp/esp-idf/export.sh  # Adjust path to your ESP-IDF installation

# Initialize and update all submodules (including nested ones)
git submodule update --init --recursive
```

### Method 1: Using ESP-IDF Command Line

```sh
# Configure backend and example
idf.py menuconfig   # Navigate to "CAN Backend" and "Example Selection"

# Build and flash
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

### Method 2: Using Python Flash Manager (Recommended for Multi-Device)

The `flash_manager.py` tool provides a comprehensive Textual-based GUI for managing ESP32 development workflows. It simplifies the entire build-flash-monitor cycle through an intuitive terminal interface, automatically detecting connected devices and handling ESP-IDF environment setup. Ideal for projects with multiple ESP32 boards requiring different configurations.

**Launch the Flash Manager:**

```sh
python3 flash_manager.py
```

#### Build & Flash Tab
![Build and flash tab](doc/build_flash.png)

The **Build & Flash** tab streamlines firmware deployment:
- Auto-detects connected ESP32 devices (ttyACM*, ttyUSB*)
- Select CAN backend (TWAI, MCP2515 single/multi) and example application per device
- Validates configuration dependencies automatically
- Manages isolated build workspaces for each backend/example combination
- Displays real-time compilation output with color-coded logging
- Handles complete workflow: configuration → build → flash in one click
- Uses optimal parallel jobs based on available CPU and memory

#### Serial Monitors Tab
![Monitor tab](doc/serial_monitors.png)

The **Serial Monitors** tab enables real-time device monitoring:
- Open multiple serial monitors simultaneously for connected devices
- Real-time output streaming with configurable buffering
- Start/Stop individual monitors without affecting others
- Hide/Show monitor logs while keeping background logging active
- Automatic port detection and fake ports for testing
- Character-by-character or buffered output display
- Supports monitoring alongside build operations

### Method 3: Automated Compilation Testing

Validate all backend/example combinations:

```sh
python3 test_compilation.py
```

This script tests all 12 possible configurations (3 example types × 4 backend configurations).

## Project Structure

```
can-multibackend-idf/
├── components/          # CAN backend libraries (git submodules)
│   ├── twai-idf-can/             # TWAI wrapper with examples
│   ├── mcp2515-esp32-idf/        # External MCP2515 single library
│   ├── mcp25xxx-multi-idf-can/   # MCP25xxx multi-device with examples
│   └── can_dispatch/             # Backend abstraction layer
├── examples/            # Example documentation and references
├── main/                # Project entry point and Kconfig configuration
├── py/                  # Python flash manager (GUI and backend logic)
├── doc/                 # Documentation and wiring diagrams
├── test_compilation.py  # Automated build testing script
└── CMakeLists.txt       # Main project CMake configuration
```

### Key Components

- **`can_dispatch/`** — Provides unified `can_twai_*` API for single-device examples, mapping calls to selected backend
- **Submodules** — Each CAN library is a git submodule with its own repository
- **Nested Submodules** — Both `twai-idf-can` and `mcp25xxx-multi-idf-can` include `examples-utils-idf-can` as a nested submodule

## License
MIT License — see [LICENSE](LICENSE)

---

*Author: Ivo Marvan, 2025*
