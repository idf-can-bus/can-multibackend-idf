#pragma once

#include "driver/gpio.h"
#include "driver/twai.h"
#include "freertos/FreeRTOS.h"
#include "can_twai_config.h"
#include "can_dispatch.h"

// Final split HW configuration in a single constant.
// Hardware configuration is set in examples/single/config_hw_twai.h.
const twai_backend_config_t CAN_HW_CFG = {
    .wiring = {
        .tx_gpio   = GPIO_NUM_39,
        .rx_gpio   = GPIO_NUM_40,
        .clkout_io = TWAI_IO_UNUSED,
        .bus_off_io= TWAI_IO_UNUSED,
    },
    .params = {
        .controller_id  = 0,
        .mode           = TWAI_MODE_NORMAL,
        .tx_queue_len   = 20,
        .rx_queue_len   = 20,
        .alerts_enabled = TWAI_ALERT_NONE, // TWAI_ALERT_RX_DATA | TWAI_ALERT_RX_FIFO_OVERRUN,
        .clkout_divider = 0,
        .intr_flags     = ESP_INTR_FLAG_LEVEL1,
    },
    .tf = {
        .timing = TWAI_TIMING_CONFIG_1MBITS(),
        .filter = TWAI_FILTER_CONFIG_ACCEPT_ALL(),
    },
    .timeouts = {
        .receive_timeout         = pdMS_TO_TICKS(100),
        .transmit_timeout        = pdMS_TO_TICKS(100),
        .bus_off_timeout         = pdMS_TO_TICKS(1000),
        .bus_not_running_timeout = pdMS_TO_TICKS(100),
    }
};



