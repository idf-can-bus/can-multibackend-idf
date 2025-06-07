#pragma once
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    CAN_BACKEND_TWAI,
    CAN_BACKEND_MCP2515_SINGLE,
    CAN_BACKEND_MCP2515_MULTI
} can_backend_type_t;

typedef struct {
    
} twai_config_t;

typedef struct {
    
} mcp2515_single_config_t;

typedef struct {
    
} mcp2515_multi_config_t;

typedef struct {
    can_backend_type_t backend;
    uint32_t bitrate;
    union {
        twai_config_t twai;
        mcp2515_single_config_t mcp_single;
        mcp2515_multi_config_t mcp_multi;
    } cfg;
} can_config_t;

#define CANIF_MAX_DATA_LEN 8
typedef struct {
    uint32_t id;                      // CAN ID (standard or extended)
    bool extended_id;                // true = 29-bit, false = 11-bit
    bool rtr;                        // Remote Transmission Request
    uint8_t dlc;                     // number of bytes (0–8)
    uint8_t data[CANIF_MAX_DATA_LEN];
} can_message_t;


// Initialize CAN hardware
bool canif_init(const can_config_t *cfg);

// non-blocking send
bool canif_send(const can_message_t *raw_out_msg);

// non-blocking receive
bool canif_receive(can_message_t *raw_in_msg);

#ifdef __cplusplus
}
#endif
