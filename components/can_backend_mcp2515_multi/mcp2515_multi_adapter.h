#pragma once
#include "can_iface.h"
#include "mcp2515-esp32_multi/mcp2515_multi.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef MCP2515_Handle mcp_multi_handle_t;

typedef struct {
    // One instance configuration
    spi_host_device_t host;
    spi_bus_config_t  bus_cfg;
    spi_device_interface_config_t dev_cfg;
    gpio_num_t        int_gpio;
    CAN_SPEED_t       can_speed;
    CAN_CLOCK_t       can_clock;
} mcp_multi_instance_cfg_t;

// Maximum number of instances supported in a single bundle
#ifndef MCP_MULTI_MAX_INSTANCES
#define MCP_MULTI_MAX_INSTANCES 8
#endif

// Bundle configuration for multiple MCP2515 instances
typedef struct {
    size_t instance_count;
    mcp_multi_instance_cfg_t instances[MCP_MULTI_MAX_INSTANCES];
} mcp_multi_bundle_cfg_t;

bool mcp2515_multi_init(const mcp_multi_instance_cfg_t* instances, size_t count);
bool mcp2515_multi_deinit(void);

// Index-based send/receive to a specific instance
bool mcp2515_multi_send(size_t index, const can_message_t* raw_out_msg);
bool mcp2515_multi_receive(size_t index, can_message_t* raw_in_msg);

#ifdef __cplusplus
}
#endif


