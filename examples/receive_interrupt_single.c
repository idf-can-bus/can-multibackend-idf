#include "can_dispatch.h"
#include "esp_log.h"
#include "examples_utils.h"
#include "init_hardware.h"
#include "sdkconfig.h"
#if CONFIG_CAN_BACKEND_TWAI
#include "twai_adapter.h"
#endif
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

/*
 * Example: receive_interrupt_single
 *
 * Backend assumptions and rationale (MCP2515 preferred):
 * - MCP2515 exposes a GPIO INT line. The adapter installs a very short ISR
 *   that marks an internal flag; all SPI access is done later in a task.
 * - This example uses a producer/consumer split to minimize latency:
 *     1) Producer task: coalesces/drains available frames as fast as possible
 *        (triggered by adapter’s IRQ internally) and enqueues them into an
 *        application queue without heavy logging.
 *     2) Consumer task: blocks on the queue and performs message processing
 *        and logging. This keeps the producer fast and avoids RX overruns.
 * - No SPI in ISR: the ISR never performs SPI; it only signals availability.
 *
 * TWAI note:
 * - The TWAI driver already uses interrupts and internal queues. The TWAI
 *   producer here simply blocks on can_twai_receive(), so the added value
 *   is mainly the unification of the pattern with MCP2515 and the possibility of a unified backpressure.
 */

static const char *TAG = "receive_interrupt_single";

// Queue capacity tuned for bursty traffic
#define RX_QUEUE_LENGTH 64

// Task configuration
#define PRODUCER_TASK_STACK 4096
#define CONSUMER_TASK_STACK 4096
#define PRODUCER_TASK_PRIO  12
#define CONSUMER_TASK_PRIO  10

static QueueHandle_t rx_queue;

static inline void received_to_queue(can_message_t *msg) {
#if CONFIG_CAN_BACKEND_TWAI
    // TWAI backend: block on driver receive (driver handles IRQ internally)
    if (can_twai_receive(msg)) {
        (void)xQueueSend(rx_queue, msg, 0);
    } else {
        // No frame within adapter timeout; yield briefly
        sleep_ms_min_ticks(1);
    }
#else
    // MCP2515 (and others): drain all currently available frames fast
    bool received_any = false;
    while (canif_receive(msg)) {
        (void)xQueueSend(rx_queue, msg, 0);
        received_any = true;
    }
    if (!received_any) {
        // If nothing was available, sleep minimally to yield CPU/IDLE
        sleep_ms_min_ticks(1);
    }
#endif
}

static void can_rx_producer_task(void *arg)
{
    can_message_t message;
    for (;;) {
        received_to_queue(&message);
    }
}

static void can_rx_consumer_task(void *arg)
{
    (void)arg;
    can_message_t message;
    const bool print_during_receive = false;

    for (;;) {
        if (xQueueReceive(rx_queue, &message, portMAX_DELAY) == pdTRUE) {
            process_received_message(&message, print_during_receive);
        }
    }
}

void app_main(void)
{
    
    // --- init hardware ----------------------------------------------------------------------------
    can_config_t hw_config;
    init_hardware(&hw_config);  // Refer to implementation for hardware initialization requirements

    // --- common init ------------------------------------------------------------------------------
    canif_init(&hw_config);

    // --- create RX queue --------------------------------------------------------------------------
    rx_queue = xQueueCreate(RX_QUEUE_LENGTH, sizeof(can_message_t));
    if (rx_queue == NULL) {
        ESP_LOGE(TAG, "Failed to create RX queue");
        return;
    }

    // identify your self as receiver
#if CONFIG_CAN_BACKEND_TWAI
    ESP_LOGI(TAG, "Receiver interrupt-driven, single controller, TWAI");
#else
    ESP_LOGI(TAG, "Receiver interrupt-driven, single controller, MCP2515");
#endif

    // --- start tasks ------------------------------------------------------------------------------
    BaseType_t ok1 = xTaskCreate(can_rx_producer_task, "can_rx_prod", PRODUCER_TASK_STACK, NULL, PRODUCER_TASK_PRIO, NULL);
    BaseType_t ok2 = xTaskCreate(can_rx_consumer_task, "can_rx_cons", CONSUMER_TASK_STACK, NULL, CONSUMER_TASK_PRIO, NULL);
    if (ok1 != pdPASS || ok2 != pdPASS) {
        ESP_LOGE(TAG, "Failed to create tasks (prod=%ld, cons=%ld)", (long)ok1, (long)ok2);
        return;
    }

    
}
