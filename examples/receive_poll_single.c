#include "can_dispatch.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include "esp_log.h"
#include "can_dispatch.h"
#include "examples_utils.h"
#include "init_hardware.h"
#include "esp_task_wdt.h"

static const char *TAG = "receive_poll_single";


void app_main(void)
{
    // Konfigurace watchdog timeru
    esp_task_wdt_config_t wdt_config = {
        .timeout_ms = 5000,           // 5 sekund timeout
        .idle_core_mask = (1 << 0),   // Sledovat idle task na CPU 0
        .trigger_panic = true         // Spustit panic handler při timeoutu
    };
    esp_task_wdt_init(&wdt_config);
    esp_task_wdt_add(NULL);      // Přidání hlavního tasku do WDT

    // --- init hardware ----------------------------------------------------------------------------
    can_config_t hw_config;
    init_hardware(&hw_config);  // Refer to implementation for hardware initialization requirements

    // --- common sender example part ---------------------------------------------------------------
    canif_init(&hw_config);

    // --- global variables -------------------------------------------------------------------------
    can_message_t message;
    uint8_t expected_heartbeat = 0;
    latency_statistic_t latency_statistic;
    bool success = false;

    // --- example settings ------------------------------------------------------------------------
    bool print_during_send = false;
    const uint32_t receive_interval_ms = 10;

    reset_latency_statistic(&latency_statistic);

    // identify your self as receiver   
    ESP_LOGI(TAG, "Receiver pool, single controller");

    while (1)
    {
        // send message
        success = canif_receive(&message);
        if (success)
        {
            process_received_message(&message, &latency_statistic, &expected_heartbeat, print_during_send);
        }
        
        // wait a while - vždy
        vTaskDelay(pdMS_TO_TICKS(receive_interval_ms));
    }
}
