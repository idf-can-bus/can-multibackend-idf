#include "mcp2515_multi_adapter.h"
#include "esp_log.h"
#include "examples_utils.h"
#include "init_hardware.h"

/*
 * Example: send_multi
 * Uses MCP2515 multi adapter with two TX controllers on SPI2 (per init_hardware.c configuration).
 */

static const char *TAG = "send_multi";

void app_main(void)
{
    // Init hardware & CAN system (explicit config)
    static can_config_t cfg;
    init_hardware(&cfg);

    const uint32_t send_interval_ms = 10;

    // Size arrays dynamically by number of instances
    uint8_t heartbeat[cfg.instance_count];
    uint8_t sender_ids[cfg.instance_count];
    for (size_t i = 0; i < cfg.instance_count; ++i) {
        heartbeat[i] = 0;
        sender_ids[i] = (uint8_t)(i + 1); // IDs 1..N
    }

    ESP_LOGI(TAG, "Multi sender, %zu TX instances", cfg.instance_count);

    can_message_t msg;
    uint64_t index = 0;
    const uint64_t stats_every = 2000;
    bool print_during_send = false;

    while (1) {
        for (size_t i=0; i<cfg.instance_count; ++i) {
            fullfill_test_messages(sender_ids[i], heartbeat[i], &msg);
            if ((index % stats_every == 0) && (index != 0)) {
                set_test_flag(&msg, TEST_FLAG_STATS_REQUEST);
            }
            bool ok = mcp2515_multi_send(i, &msg);
            if (!ok) {
                ESP_LOGE(TAG, "TX%u: send failed", (unsigned)i);
                print_can_message(&msg);
            } else {
                debug_send_message(&msg, print_during_send);
                heartbeat[i] = next_heartbeat(heartbeat[i]);
            }
        }
        index++;
        sleep_ms_min_ticks(send_interval_ms);
    }
}
