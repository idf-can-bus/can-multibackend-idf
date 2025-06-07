#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "can_iface.h"

#include "sdkconfig.h"
#if CONFIG_CAN_BACKEND_TWAI
#include "can_backend_twai.h"
#endif

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"


#ifdef __cplusplus
extern "C" {
#endif


#if CONFIG_CAN_BACKEND_TWAI
    /* call TWAI backend */
    typedef twai_config_t can_config_t;
#elif CONFIG_CAN_BACKEND_MCP2515
    /* call MCP2515 backend */
#elif CONFIG_CAN_BACKEND_MCP_MULTI
    /* call multi-MCP backend */
#elif CONFIG_CAN_BACKEND_ARDUINO
    /* call Arduino backend */
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
