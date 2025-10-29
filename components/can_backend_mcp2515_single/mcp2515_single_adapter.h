#pragma once
#include "can_message.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "components/can_backend_mcp2515_multi/mcp2515_config_types.h"

#ifdef __cplusplus
extern "C" {
#endif


// Initialize MCP2515
bool mcp2515_single_init(const mcp2515_bundle_config_t *cfg);

// Deinitialize MCP2515
bool mcp2515_single_deinit();

// Send message
bool mcp2515_single_send(const can_message_t *raw_out_msg);

// Receive message
bool mcp2515_single_receive(can_message_t *raw_in_msg);

#ifdef __cplusplus
}
#endif