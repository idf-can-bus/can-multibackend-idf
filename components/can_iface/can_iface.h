#pragma once
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CANIF_MAX_DATA_LEN 8
typedef struct {
    uint32_t id;                      // CAN ID (standard or extended)
    bool extended_id;                // true = 29-bit, false = 11-bit
    bool rtr;                        // Remote Transmission Request
    uint8_t dlc;                     // number of bytes (0–8)
    uint8_t data[CANIF_MAX_DATA_LEN];
} can_message_t;

#ifdef __cplusplus
}
#endif