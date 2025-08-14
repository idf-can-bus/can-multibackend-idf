#include "can_dispatch.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include "esp_log.h"
#include "can_dispatch.h"
#include "examples_utils.h"
#include "init_hardware.h"

static const char *TAG = "send_single";


void app_main(void)
{

    // --- init hardware ----------------------------------------------------------------------------
    can_config_t hw_config;
    init_hardware(&hw_config);  // Refer to implementation for hardware initialization requirements

    // --- common sender example part ---------------------------------------------------------------
    canif_init(&hw_config);

    // --- global variables -------------------------------------------------------------------------
    can_message_t message;
    uint8_t heartbeat = 0;
    bool success = false;

    // --- example settings ------------------------------------------------------------------------
    const uint32_t send_interval_ms = 10;
    bool print_during_send = false;
    uint64_t index = 0;
    const uint64_t max_index = 1000;
    sender_id_t sender_id = SENDER_ID_1;

    // identify your self as sender
    ESP_LOGI(TAG, "Sender ID: %d", sender_id);

    while (1)
    {
        // create message
        fullfill_test_messages(sender_id, heartbeat, &message);

        // send it
        success = canif_send(&message);
        if (!success)
        {
            ESP_LOGE(TAG, "Failed to send message");
            print_can_message(&message);

            // next heartbeat
            heartbeat = next_heartbeat(heartbeat);
        }
        else {
            debug_send_message(&message, print_during_send);
            index++;
        }

        // Sometimes send extra tag for latency measurement
        sender_id = (index % max_index == 0) ? END_TAG_ID : SENDER_ID_1;

        // wait for send interval
        vTaskDelay(pdMS_TO_TICKS(send_interval_ms));
    }
}
