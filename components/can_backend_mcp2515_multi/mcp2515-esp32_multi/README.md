# mcp2515-esp32_multi

Multi-instance MCP2515 driver for ESP-IDF (opaque handles, no globals).

Based on original single-instance project:
- https://github.com/latonita/mcp2515-esp32-idf

This fork adds:
- Multiple MCP2515 instances across one or more SPI hosts
- Minimal event API (WaitForEvent, SetEventCallback)
- SPI helpers for easy bring-up
- Strictly no SPI access in ISR; ISR only signals events

Use an adapter/examples to wire tasks/queues.

