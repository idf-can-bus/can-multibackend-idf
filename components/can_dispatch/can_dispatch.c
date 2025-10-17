#include "can_dispatch.h"
#include "sdkconfig.h"
#if CONFIG_CAN_BACKEND_MCP2515_MULTI
#include "mcp2515_multi_adapter.h"
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
    /* call multi-MCP backend */
    // Initialize one instance (index 0) using provided cfg
    return mcp2515_multi_init((const mcp_multi_instance_cfg_t*)cfg, 1);
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
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
    /* call multi-MCP backend */
    return mcp2515_multi_deinit();
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
#endif
    return false;
}

// non-blocking send
bool canif_send(const can_message_t *raw_out_msg)
{
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    return can_twai_send(raw_out_msg);
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515_SINGLE backend */
    return mcp2515_single_send(raw_out_msg);
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call multi-MCP backend */
    return mcp2515_multi_send(0, raw_out_msg);
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
#endif
    return false;
}

// non-blocking receive
bool canif_receive(can_message_t *raw_in_msg)
{
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    return can_twai_receive(raw_in_msg);
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    /* call MCP2515_SINGLE backend */
    return mcp2515_single_receive(raw_in_msg);
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    /* call multi-MCP backend */
    return mcp2515_multi_receive(0, raw_in_msg);
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
#endif
    return false;
}
