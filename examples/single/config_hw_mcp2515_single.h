#pragma once

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "mcp2515-esp32-idf/mcp2515.h"
#include "components/can_backend_mcp2515_multi/mcp2515_config_types.h"

// Single definition: bundle with one device (unified MCP2515 config types)
static const mcp2515_bundle_config_t BUS_CFG = {
    .bus = {
        .wiring = {
            .miso_io_num = GPIO_NUM_37,
            .mosi_io_num = GPIO_NUM_38,
            .sclk_io_num = GPIO_NUM_36,
            .quadwp_io_num = -1,
            .quadhd_io_num = -1,
        },
        .params = {
            .host = SPI2_HOST,
            .max_transfer_sz = 0,
            .flags = SPICOMMON_BUSFLAG_MASTER,
            .dma_chan = SPI_DMA_CH_AUTO,
            .intr_flags = 0,
            .isr_cpu_id = 0,
        },
        .manage_bus_lifetime = true,
    },
    .devices = (const mcp2515_device_config_t[]){
        {
            .wiring = {
                .cs_gpio = GPIO_NUM_33,
                .int_gpio = GPIO_NUM_34,
                .stby_gpio = (gpio_num_t)-1,
                .rst_gpio = (gpio_num_t)-1,
            },
            .spi_params = {
                .mode = 0,
                .clock_speed_hz = 10000000,
                .queue_size = 1024,
                .flags = 0,
                .command_bits = 0,
                .address_bits = 0,
                .dummy_bits = 0,
            },
            .hw = { .crystal_frequency = MCP_16MHZ },
            .can = { .can_speed = CAN_1000KBPS, .use_loopback = false },
        }
    },
    .device_count = 1,
};


