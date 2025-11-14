#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "driver/twai.h"
#include "sdkconfig.h"


// Include the example's header-only HW configuration based on selected backend.
#if CONFIG_CAN_BACKEND_TWAI

#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE

#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
#if CONFIG_EXAMPLE_SEND_MULTI
#include "multi/config_hw_mcp2515_multi_send.h"
#elif CONFIG_EXAMPLE_RECV_POLL_MULTI || CONFIG_EXAMPLE_RECV_INT_MULTI
#include "multi/config_hw_mcp2515_multi_receive.h"
#else
#include "single/config_hw_mcp2515_multiple.h" // fallback: single-device on multi backend
#endif
#endif

#if CONFIG_CAN_BACKEND_TWAI
#include "can_twai_config.h"
#include "can_twai.h"
#include "single/config_hw_twai.h" // the default configuration for the TWAI backend
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
// Use unified MCP2515 config types for all MCP2515 variants
#include "mcp2515_multi.h"
#include "mcp2515_single_adapter.h"
#include "single/config_hw_mcp2515_single.h" // the default configuration for the MCP2515_SINGLE backend
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
// Multi MCP2515 backend interface (bus/dev registry + messaging)
#include "mcp2515_multi.h"
#if CONFIG_EXAMPLE_SEND_MULTI || CONFIG_EXAMPLE_SEND_SINGLE
#include "multi/config_hw_mcp2515_multi_send.h" // the default configuration for the MCP2515_MULTI backend
#elif CONFIG_EXAMPLE_RECV_POLL_MULTI || CONFIG_EXAMPLE_RECV_INT_MULTI || CONFIG_EXAMPLE_RECV_POLL_SINGLE || CONFIG_EXAMPLE_RECV_INT_SINGLE
#include "multi/config_hw_mcp2515_multi_receive.h" // the default configuration for the MCP2515_MULTI backend
#else
#error "Unknown example for the MCP2515_MULTI backend"
#endif
#else 
#error "Unknown backend"
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
#endif

// --- Polymorphic functions for handling CAN hardware --------------------------------------------

// Initialize CAN hardware
bool canif_init(const can_config_t *cfg);

// Deinitialize CAN hardware
bool canif_deinit();

// non-blocking send
bool canif_send(const twai_message_t *msg);

// non-blocking receive
bool canif_receive(twai_message_t *msg);

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
