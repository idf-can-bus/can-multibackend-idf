#include "can_dispatch.h"
#include "sdkconfig.h"
#if CONFIG_CAN_BACKEND_MCP2515_MULTI
#include "mcp2515_multi.h"
#endif

// Initialize CAN hardware
bool canif_init(const can_config_t *cfg)
{
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    return can_twai_init(cfg);
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515_SINGLE backend */
    return mcp2515_single_init(cfg);
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call multi-MCP backend (new interface) */
    return canif_multi_init_default((const mcp2515_bundle_config_t*)cfg);
#endif
    return false;
}

// Deinitialize CAN hardware
bool canif_deinit()
{
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    return can_twai_deinit();
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515_SINGLE backend */
    return mcp2515_single_deinit();
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call multi-MCP backend (new interface) */
    return canif_multi_deinit_default();
#endif
    return false;
}

// non-blocking send
bool canif_send(const twai_message_t *msg)
{
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    return can_twai_send(msg);
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515_SINGLE backend */
    return mcp2515_single_send(msg);
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call multi-MCP backend (new interface) */
    return canif_multi_send_default(msg);
#endif
    return false;
}

// non-blocking receive
bool canif_receive(twai_message_t *msg)
{
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    return can_twai_receive(msg);
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515_SINGLE backend */
    return mcp2515_single_receive(msg);
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call multi-MCP backend (new interface) */
    // For now, use default device receive
    return canif_receive_default(msg);
#endif
    return false;
}
