#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "can_message.h"

#include "sdkconfig.h"
#if CONFIG_CAN_BACKEND_TWAI
#include "twai_config_types.h"
#include "twai_adapter.h"
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
// Use unified MCP2515 config types for all MCP2515 variants
#include "components/can_backend_mcp2515_multi/mcp2515_config_types.h"
#include "mcp2515_single_adapter.h"
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
// Use unified MCP2515 config types for all MCP2515 variants
#include "components/can_backend_mcp2515_multi/mcp2515_config_types.h"
#include "mcp2515_multi_adapter.h"
#elif CONFIG_CAN_BACKEND_ARDUINO
#include "can_backend_arduino.h"
#endif

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"



#ifdef __cplusplus
extern "C" {
#endif

// CAN configuration type (it is polymorphic, based on the selected backend)
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    typedef twai_backend_config_t can_config_t;
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515 backend (single) using unified bundle */
    typedef mcp2515_bundle_config_t can_config_t;
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call MCP2515 backend (multi) using unified bundle */
    typedef mcp2515_bundle_config_t can_config_t;
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
    // TODO: Define Arduino config type
#endif

// --- Polymorphic functions for handling CAN hardware --------------------------------------------

// Initialize CAN hardware
bool canif_init(const can_config_t *cfg);

// Deinitialize CAN hardware
bool canif_deinit();

// non-blocking send
bool canif_send(const can_message_t *raw_out_msg);

// non-blocking receive
bool canif_receive(can_message_t *raw_in_msg);

// --- Commomn variable and functions for all backends --------------------------------------------
// Holder for hardware configuration, can be used to initialize hardware
// The type of this variable is polymorphic, based on the selected backend
extern const can_config_t CAN_HW_CFG;

// Get hardware configuration
static inline const can_config_t* get_hw_config(void) { return &CAN_HW_CFG; }

// Initialize hardware
static inline void init_hw(void) { canif_init(&CAN_HW_CFG); }

#ifdef __cplusplus
}
#endif
