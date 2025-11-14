#pragma once

#include <stdint.h>
#include <string.h>
#include "driver/twai.h"

#ifdef __cplusplus
extern "C" {
#endif


// ------------------------------------------------------------------------------------------------
// Define different accesses to CAN payload (data from CAN frame)
// We use all messages with 8 bytes payload

// for common tests
#define TEST_MSG_ID ((uint8_t)1)
typedef uint8_t unit40_big_endian_t[5];

// Flags API
typedef enum {
    TEST_FLAG_STATS_REQUEST = 1u << 0,
    TEST_FLAG_RESERVED_1    = 1u << 1,
    TEST_FLAG_RESERVED_2    = 1u << 2,
    TEST_FLAG_RESERVED_3    = 1u << 3,
} test_flag_bits_t;

typedef struct {
    uint8_t value;
} test_flags_t;

static inline void test_flags_set(test_flags_t *f, test_flag_bits_t bit) { f->value |= (uint8_t)bit; }
static inline void test_flags_clear(test_flags_t *f, test_flag_bits_t bit) { f->value &= (uint8_t)~bit; }
static inline bool test_flags_is_set(const test_flags_t *f, test_flag_bits_t bit) { return (f->value & (uint8_t)bit) != 0; }

// Test frame payload layout (8 bytes total):
//  byte0: sender_id
//  byte1: heartbeat (uint8_t)
//  byte2: flags (see test_flag_bits_t)
//  byte3..7: timestamp40 (big-endian, 40-bit)
typedef struct __attribute__((packed)) {
    uint8_t sender_id;          // 1. byte
    uint8_t heartbeat;          // 2. byte
    test_flags_t flags;         // 3. byte
    unit40_big_endian_t timestamp40; // 4. - 8. byte
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
// store 40 least significant bits of 64bit value into 5B array (big-endian)
void store_timestamp40(uint64_t source, unit40_big_endian_t *target_ptr);


// restore 5B big-endian timestamp back to 64bit value
uint64_t restore_timestamp40(const unit40_big_endian_t *src_ptr);

// ------------------------------------------------------------------------------------------------

// Generate new test message
void fullfill_test_messages(uint8_t sender_id, uint8_t heartbeat, twai_message_t *message);
// Helpers to manipulate flags in prepared message
static inline void set_test_flag(twai_message_t *message, uint8_t flag)
{
    test_can_message_t *p = (test_can_message_t*)message->data;
    test_flags_set(&p->flags, (test_flag_bits_t)flag);
}


// Print CAN message for debug purposes
void print_can_message(const twai_message_t *message);


// --- chack heartbeat ----------------------------------------------------------------------------
bool check_heartbeat(uint8_t received_heartbeat, uint8_t expected_heartbeat);
uint8_t next_heartbeat(const uint8_t heartbeat);

// process received message in a example 
void process_received_message(twai_message_t *message, const bool print_during_receive);

// process received message from multiple senders (per-sender statistics and logging)
void process_received_message_multi(twai_message_t *message, const bool print_during_receive);

// debug send message
void debug_send_message(twai_message_t *message, const bool print_during_send);

// log message in a example 
void log_message(const bool send, twai_message_t *message, const bool print_details);

// Derive default sender_id from device MAC: returns 0..255 
uint8_t default_sender_id_from_mac(void);

// Sleep for given milliseconds ensuring at least one RTOS tick is waited
void sleep_ms_min_ticks(uint32_t ms);

#ifdef __cplusplus
}
#endif