#include "can_dispatch.h"
#include "esp_log.h"
#include "examples_utils.h"
#include "init_hardware.h"

static const char *TAG = "send_single";


void app_main(void)
{

    // --- init hardware & CAN system (explicit config) --------------------------------------------
    static can_config_t cfg;
    init_hardware(&cfg);

    // --- global variables -------------------------------------------------------------------------
    can_message_t message;
    uint8_t heartbeat = 0;
    bool success = false;

    // --- example settings ------------------------------------------------------------------------
    const uint32_t send_interval_ms = 10;
    bool print_during_send = false;
    uint64_t index = 0;
    const uint64_t max_index = 2000;
    uint8_t sender_id = default_sender_id_from_mac();

    // identify your self as sender
    ESP_LOGI(TAG, "Sender ID: %d", sender_id);

    while (1)
    {
        // create message 
        fullfill_test_messages(sender_id, heartbeat, &message);
        // Request statistics periodically
        if ((index % max_index == 0) && (index != 0)) {
            set_test_flag(&message, TEST_FLAG_STATS_REQUEST);
        }

        // send it
        success = canif_send(&message);
        if (!success)
        {
            ESP_LOGE(TAG, "Failed to send message");
            print_can_message(&message);

        }
        else {
            debug_send_message(&message, print_during_send);
            index++;
        }

        // next heartbeat
        heartbeat = next_heartbeat(heartbeat);

        // (tag is handled per-message via current_sender above)

        // wait for send interval
        sleep_ms_min_ticks(send_interval_ms);
    }
}
