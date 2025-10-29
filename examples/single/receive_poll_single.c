
#include "esp_log.h"
#include "examples_utils.h"
#include "can_dispatch.h"
#include "hw_init_by_settings.h"

static const char *TAG = "receive_poll_single";


void app_main(void)
{
    // WDT is managed by system defaults; this example does not reconfigure it.

    // --- init hardware (header-only config) -------------------------------------------------------
    init_hw();

    // --- global variables -------------------------------------------------------------------------
    can_message_t message;
    bool success = false;

    // --- example settings ------------------------------------------------------------------------
    bool print_during_send = false;
    const uint32_t receive_interval_ms = 1;


    // identify your self as receiver   
    ESP_LOGI(TAG, "Receiver pool driven");

    while (1)
    {
        // send message
        success = canif_receive(&message);
        if (success)
        {
            process_received_message(&message, print_during_send);
        }

        // wait a while
        sleep_ms_min_ticks(receive_interval_ms);
    }
}
