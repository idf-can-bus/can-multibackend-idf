#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "can_iface.h"

#include "sdkconfig.h"
#if CONFIG_CAN_BACKEND_TWAI
#include "twai_adapter.h"
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
#include "mcp2515_single_adapter.h"
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
#include "mcp2515_multi_adapter.h"
#elif CONFIG_CAN_BACKEND_ARDUINO
#include "can_backend_arduino.h"
#endif

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"



#ifdef __cplusplus
extern "C" {
#endif


#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    typedef twai_config_t can_config_t;
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515 backend */
    typedef mcp2515_single_config_t can_config_t;
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call multi-MCP backend */
    typedef mcp2515_single_config_t can_config_t;  // Use same config for now
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
    // TODO: Define Arduino config type
#endif

// Initialize CAN hardware
bool canif_init(const can_config_t *cfg);

// Deinitialize CAN hardware
bool canif_deinit();

// non-blocking send
bool canif_send(const can_message_t *raw_out_msg);

// non-blocking receive
bool canif_receive(can_message_t *raw_in_msg);

#ifdef __cplusplus
}
#endif
