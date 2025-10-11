#include <stddef.h>
#include <limits.h>
#include "esp_timer.h"
#include "esp_log.h"
#include "examples_utils.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TAG "EXAMPLES_UTILS"

// store 48 least significant bits of 64bit value into 6B array (big-endian)
void store_timestamp48(uint64_t source, unit48_big_endian_t *target_ptr)
{
    for (int i = 0; i < 6; ++i)
        (*target_ptr)[5 - i] = (source >> (i * 8)) & 0xFF;
}

// restore 6B big-endian timestamp back to 64bit value
uint64_t restore_timestamp48(const unit48_big_endian_t *src_ptr)
{
    uint64_t result = 0;
    for (int i = 0; i < 6; ++i)
        result = (result << 8) | (*src_ptr)[i];
    return result;
}

void fullfill_test_messages(uint8_t sender_id, uint8_t heartbeat, can_message_t *message) 
{
    if (message == NULL) {
        ESP_LOGE(TAG, "Invalid frame pointer");
        return;
    }

    // view to message->data (8 bytes) as a test_can_message_t
    test_can_message_t * payload = (test_can_message_t *)message->data;

    message->id = TEST_MSG_ID;
    message->extended_id = false;
    message->rtr = false;
    message->dlc = 8;
    payload->sender_id = sender_id;
    payload->heartbeat = heartbeat;
    store_timestamp48(esp_timer_get_time(), & (payload->timestamp));
} // get_test_messages

void print_can_message(const can_message_t *message) {
    if (message == NULL) {
        ESP_LOGE(TAG, "Invalid frame pointer");
        return;
    }
    
    printf("CAN message ID: %lu\n", message->id);
    switch (message->id) {
        case TEST_MSG_ID:
            // view payload as test_can_message_t
            test_can_message_t *payload1 = (test_can_message_t *)message->data;

            printf("Test message\n");
            printf("Sender ID: %u\n", payload1->sender_id);
            printf("Heartbeat: %u\n", payload1->heartbeat);
            printf("Timestamp: %llu [us]\n", restore_timestamp48(& (payload1->timestamp)));
            break;

        case CAN_MSG_WITH_TWO_UINT32_ID:
            // view payload as can_message_with_two_uint32_t
            can_message_with_two_uint32_t *payload2 = (can_message_with_two_uint32_t *)message->data;
            printf("Two uint32 message\n");
            printf("Value uint32_1: %lu\n", payload2->value_uint32_1);
            printf("Value uint32_2: %lu\n", payload2->value_uint32_2);
            break;

        case CAN_MSG_WITH_ONE_UINT64_ID:
            // view payload as can_message_with_one_uint64_t
            can_message_with_one_uint64_t *payload3 = (can_message_with_one_uint64_t *)message->data;

            printf("One uint64 message\n");
            printf("Value uint64: %llu\n", payload3->value_uint64);
            break;

        case EIGHT_BYTES_ARRAY_MESSAGE_ID:
            // view payload as eight_bytes_array_message_t
            eight_bytes_array_message_t *payload4 = (eight_bytes_array_message_t *)message->data;

            printf("Eight bytes array message\n");
            printf("Data:");
            for (int i = 0; i < 8; i++) {
                printf(" %02X", payload4->data[i]);
            }
            printf("\n");
            break;

        default:
            printf("Unknown message ID: %lu\n", message->id);
            break;
    }
        // debug print message->data
    printf("message->data (dec):|");
    for (int i = 0; i < message->dlc; i++) {
        printf("%03d|", message->data[i]);
    }
    printf("\n");
}

bool check_heartbeat(uint8_t received_heartbeat, uint8_t expected_heartbeat)
{
    bool success = received_heartbeat == expected_heartbeat;
    if (!success) {
        ESP_LOGE(TAG, "Heartbeat mismatch: expected_heartbeat %u, payload->heartbeat %u", expected_heartbeat, received_heartbeat);
    } 
    
    return success;
}

// Here we assume that heartbeat is uint8_t in range 0-255
uint8_t next_heartbeat(const uint8_t heartbeat) {
    return heartbeat + 1;  // uint8_t automatically wraps 255->0
}

static uint64_t count_of_messages_for_log = 0;
#define PRINT_DOT_EVERY_N_MESSAGES 10
#define MAX_INDEX_ON_ONE_LINE 50
#define PRINT_NL_EVERY_N_MESSAGES (PRINT_DOT_EVERY_N_MESSAGES*MAX_INDEX_ON_ONE_LINE)


void log_message(const bool send, can_message_t *message, const bool print_details) {
    if (print_details) {
        print_can_message(message);
    } else {
        if (count_of_messages_for_log % PRINT_DOT_EVERY_N_MESSAGES == 0) {
            printf(".");
        }
        if (count_of_messages_for_log % PRINT_NL_EVERY_N_MESSAGES == 0) {
            if (send) {
                printf("\n->");                
            } else {
                printf("\n<-");                                
            }
            printf(" (%lld) ", count_of_messages_for_log);
        }        
        fflush(stdout);
        count_of_messages_for_log++;
    }
}

// Sequence statistics 
static uint64_t seq_rx_count = 0;                 // total payload->heartbeat TEST_MSG_ID frames
static uint64_t seq_ok_in_order = 0;              // frames arriving exactly in expected_heartbeat order
static uint64_t seq_lost = 0;                     // estimated number of lost frames (forward jump delta)
static uint64_t seq_out_of_order_or_dup = 0;      // frames that appear behind expected_heartbeat (out-of-order or duplicate)
static uint64_t seq_start_time_us = 0;            // Start time for sequence statistics
static uint8_t expected_heartbeat = 0;            // expected_heartbeat heartbeat


void process_received_message(can_message_t *message, const bool print_during_receive) {
    if (message == NULL) {
        ESP_LOGE(TAG, "Invalid message pointer");
        return;
    }
    if (print_during_receive) {
        print_can_message(message);
    } else {
        log_message(false, message, print_during_receive);        
    }
    if (message->id == TEST_MSG_ID) {
        test_can_message_t *payload = (test_can_message_t *)message->data;

        // Sequence check 
        // Calculate delta as signed difference with proper overflow handling
        // Positive delta: payload->heartbeat > expected_heartbeat (lost frames)
        // Negative delta: payload->heartbeat < expected_heartbeat (out-of-order/duplicate frames)
        int16_t delta = (int16_t)payload->heartbeat - (int16_t)expected_heartbeat;
        if (delta < -127) delta += 256;  // Handle uint8_t overflow
        if (delta > 127) delta -= 256;   // Handle uint8_t overflow

        // @TODO: remove this debug print
        /*
        if (! check_heartbeat(payload->heartbeat, expected_heartbeat)) {
            ESP_LOGE(TAG, "%d != %d, delta: %d", payload->heartbeat, expected_heartbeat, delta);
        }
        */
       
        seq_rx_count++;
        if (seq_start_time_us == 0) {
            seq_start_time_us = esp_timer_get_time();  // Start timing on first message
            seq_rx_count = 0;  // Reset counter to 1 for first message
        }
        
        if (delta == 0) {
            seq_ok_in_order++;
        } else if (delta > 0) {
            seq_lost += delta;  // Positive delta = lost frames
        } else {
            seq_out_of_order_or_dup++;  // Negative delta = out-of-order/duplicate
        }

        // Advance expected_heartbeat to next after the payload->heartbeat
        expected_heartbeat = next_heartbeat(payload->heartbeat);

        // Print and reset stats on END tag
        if (payload->sender_id == END_TAG_ID) {
            uint64_t current_time = esp_timer_get_time();
            uint64_t elapsed_time_us = current_time - seq_start_time_us;
            float elapsed_time_ms = (float)elapsed_time_us / 1000.0f;
            float rx_rate_hz = 0.0f;
            
            if (elapsed_time_ms > 0) {
                rx_rate_hz = (float)seq_rx_count / (elapsed_time_ms / 1000.0f);
            }
            printf("\n");
            // Print stats in a single log line to minimize blocking time and reduce RX overruns
            ESP_LOGI(TAG,
                     "Sequence stats: frames=%llu in_order=%llu lost=%llu dup=%llu elapsed=%.1f ms rx=%.1f Hz",
                     seq_rx_count,
                     seq_ok_in_order,
                     seq_lost,
                     seq_out_of_order_or_dup,
                     elapsed_time_ms,
                     rx_rate_hz);
            
            // Reset sequence statistics window
            seq_rx_count = 0;
            seq_ok_in_order = 0;
            seq_lost = 0;
            seq_out_of_order_or_dup = 0;
            seq_start_time_us = current_time;  // Start new measurement window
        }
    } 
}

void debug_send_message(can_message_t *message, const bool print_during_send) {
    if (message == NULL) {
        ESP_LOGE(TAG, "Invalid frame pointer");
        return;
    }
    log_message(true, message, print_during_send);
}

void sleep_ms_min_ticks(uint32_t ms)
{
    TickType_t ticks = pdMS_TO_TICKS(ms);
    if (ticks == 0) {
        ticks = 1;
    }
    vTaskDelay(ticks);
}