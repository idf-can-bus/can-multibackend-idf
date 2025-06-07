#pragma once
#include "can_iface.h"
#include "driver/twai.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    twai_general_config_t general_config;  // General TWAI configuration
    twai_timing_config_t timing_config;    // Timing configuration (baudrate)
    twai_filter_config_t filter_config;    // Message filter configuration
    TickType_t receive_timeout;            // Timeout for receiving messages
    TickType_t transmit_timeout;           // Timeout for transmitting messages  
    TickType_t bus_off_timeout;            // Timeout for bus-off recovery
    TickType_t bus_not_running_timeout;    // Timeout for bus-not-running recovery
} twai_config_t;


// Initialize CAN hardware
bool can_twai_init(const twai_config_t *cfg);

// Deinitialize CAN hardware
bool can_twai_deinit();

// non-blocking send
bool can_twai_send(const can_message_t *raw_out_msg);

// non-blocking receive
bool can_twai_receive(can_message_t *raw_in_msg);

/**
 * Checks TWAI controller status and resets it if necessary.
 * This handles bus-off conditions and restarts the controller
 * if it's not in the running state.
 */
void can_twai_reset_twai_if_needed(void);

#ifdef __cplusplus
}
#endif