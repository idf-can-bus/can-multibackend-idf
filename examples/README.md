# CAN Examples

This directory contains references to CAN example applications for different backends.

## 📦 Example Locations

Examples are maintained in their respective component repositories to avoid duplication and ensure consistency.

---

## 🔷 Single-Device TWAI Examples

**Location:** [`components/twai-idf-can/examples/`](../components/twai-idf-can/examples/)

Examples using ESP32's built-in TWAI (CAN) controller:

- **send** - Send CAN messages with heartbeat and timestamp
- **receive_poll** - Receive messages using polling mode
- **receive_interrupt** - Receive messages using interrupt-driven queue

**API:** Direct `can_twai_*` functions  
**Hardware:** ESP32/S3/C3/C6 with CAN transceiver (e.g., SN65HVD230)  
**Configuration:** [`config_twai.h`](../components/twai-idf-can/examples/config_twai.h)

---

## 🔶 Multi-Device MCP2515 Examples

**Location:** [`components/mcp25xxx-multi-idf-can/examples/`](../components/mcp25xxx-multi-idf-can/examples/)

Examples using multiple MCP2515 CAN controllers via SPI:

- **send** - Send from multiple TX controllers simultaneously
- **receive_poll** - Receive from multiple RX controllers (polling)
- **receive_interrupt** - Receive from multiple RX controllers (interrupt)

**API:** Multi-device `canif_*` functions  
**Hardware:** Multiple MCP2515 (or MCP25625) via SPI  
**Configuration:** 
- [`config_send.h`](../components/mcp25xxx-multi-idf-can/examples/config_send.h) - TX setup
- [`config_receive.h`](../components/mcp25xxx-multi-idf-can/examples/config_receive.h) - RX setup

---

## 🔄 Unified Multi-Backend Support

This project (`can-multibackend-idf`) provides a **unified dispatcher** that allows switching between different CAN backends (TWAI, MCP2515 single/multi) via Kconfig configuration.

**For unified examples using the dispatcher layer**, refer to the individual component examples above, as each backend has its own optimized API:

- **TWAI**: Direct hardware access via `can_twai_*`
- **MCP2515 Multi**: Multi-device registry via `canif_*`
- **MCP2515 Single**: Uses external library via dispatcher

---

## 🛠 Utilities

**Location:** [`components/examples_utils/`](../components/examples_utils/)

Shared utilities for all examples:
- Test message generation (`fullfill_test_messages`)
- Sequence checking and statistics (`process_received_message`)
- Multi-sender tracking (`process_received_message_multi`)
- MAC-based sender ID generation

---

## 📚 Related Documentation

- [TWAI Component README](../components/twai-idf-can/README.md)
- [MCP25xxx Multi Component README](../components/mcp25xxx-multi-idf-can/README.md)
- [Main Project README](../README.md)

---

*For standalone usage of individual components, see the README in each component's directory.*

