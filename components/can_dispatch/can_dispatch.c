#include "can_dispatch.h"
#include "sdkconfig.h"

// Initialize CAN hardware
bool canif_init(const can_config_t *cfg)
{
#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
#elif CONFIG_CAN_BACKEND_MCP2515
    /* call MCP2515 backend */
#elif CONFIG_CAN_BACKEND_MCP_MULTI
    /* call multi-MCP backend */
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
#endif
    return false;
}

// non-blocking send
bool canif_send(const can_message_t *raw_out_msg)
{
    return false;
}

// non-blocking receive
bool canif_receive(can_message_t *raw_in_msg)
{
    return false;
}


