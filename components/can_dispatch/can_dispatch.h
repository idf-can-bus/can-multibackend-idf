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



// type for wiring SPI bus for MCP2515
typedef struct {
    gpio_num_t miso_io;
    gpio_num_t mosi_io;
    gpio_num_t sclk_io;
    gpio_num_t spics_io;
} spi_bus_config_t;





typedef struct {
    size_t instance_count; // Always present; 1 for TWAI/SINGLE, N for MULTI
#if CONFIG_CAN_BACKEND_TWAI
    twai_config_t twai;
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    mcp2515_single_config_t single;
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
    mcp_multi_bundle_cfg_t multi;
#elif CONFIG_CAN_BACKEND_ARDUINO
    // TODO: add Arduino config if/when enabled
#endif
} can_config_t;

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
