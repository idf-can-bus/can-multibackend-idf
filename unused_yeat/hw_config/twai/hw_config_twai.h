// Wiring and configuration for TWAI controller
#pragma once
#include "driver/twai.h"
#include "driver/gpio.h"
#include "init_hardware.h"

typedef struct {
    gpio_num_t tx_io;
    gpio_num_t rx_io;
} twai_wiring_config_t;

configure_hardware_twai(can_config_t *hw_config_ptr)