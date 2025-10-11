#pragma once

#include <stdint.h>
#include <string.h>
#include "can_iface.h"

#ifdef __cplusplus
extern "C" {
#endif


// ------------------------------------------------------------------------------------------------
// Define different accesses to CAN payload (data from CAN frame)
// We use all messages with 8 bytes payload

// for common tests
#define TEST_MSG_ID ((uint8_t)1)
typedef uint8_t unit48_big_endian_t[6];

typedef struct __attribute__((packed)) {
    uint8_t sender_id; // 1. byte
    uint8_t heartbeat; // 2. byte
    unit48_big_endian_t timestamp; // 3. - 8. byte
} test_can_message_t;

// other example of message access/definition
#define CAN_MSG_WITH_TWO_UINT32_ID ((uint8_t)2)
typedef struct  __attribute__((packed)) {
    uint32_t value_uint32_1;  // 1. - 4. byte
    uint32_t value_uint32_2;  // 5. - 8. byte
} can_message_with_two_uint32_t;

// other example of message access/definition
#define CAN_MSG_WITH_ONE_UINT64_ID ((uint8_t)3)
typedef struct  __attribute__((packed)) {
    uint64_t value_uint64;    // 1. - 8. byte
} can_message_with_one_uint64_t; 

// other example of message access/definition
#define EIGHT_BYTES_ARRAY_MESSAGE_ID ((uint8_t)4)
typedef struct  __attribute__((packed)) {
    uint8_t data[8];         // 1. - 8. byte
} eight_bytes_array_message_t;

// different logical access to CAN message payload
typedef union {
    test_can_message_t test_message;
    can_message_with_two_uint32_t two_uint32_message;
    can_message_with_one_uint64_t one_uint64_message;
    eight_bytes_array_message_t eight_bytes_array_message;
} can_message_payload_t;

// --- access to unit48_big_endian_t ------------------------------------------------------------
// store 48 least significant bits of 64bit value into 6B array (big-endian)
void store_timestamp48(uint64_t source, unit48_big_endian_t *target_ptr);


// restore 6B big-endian timestamp back to 64bit value
uint64_t restore_timestamp48(const unit48_big_endian_t *src_ptr);

// ------------------------------------------------------------------------------------------------

// Generate new test message
void fullfill_test_messages(uint8_t sender_id, uint8_t heartbeat, can_message_t *message);

// Print CAN message for debug purposes
void print_can_message(const can_message_t *message);


// --- chack heartbeat ----------------------------------------------------------------------------
bool check_heartbeat(uint8_t received_heartbeat, uint8_t expected_heartbeat);
uint8_t next_heartbeat(const uint8_t heartbeat);

// process received message in a example 
void process_received_message(can_message_t *message, const bool print_during_receive);

// debug send message
void debug_send_message(can_message_t *message, const bool print_during_send);

// log message in a example 
void log_message(const bool send, can_message_t *message, const bool print_details);

// Sleep for given milliseconds ensuring at least one RTOS tick is waited
void sleep_ms_min_ticks(uint32_t ms);

// --- enumerate senders ---------------------------------------------------------------------------
typedef enum {
    SENDER_ID_1 = 1,
    SENDER_ID_2 = 2,
    SENDER_ID_3 = 3,
    SENDER_ID_4 = 4,
    SENDER_ID_5 = 5,
    SENDER_ID_6 = 6,
    END_TAG_ID = 255,
} sender_id_t;






#ifdef __cplusplus
}
#endif