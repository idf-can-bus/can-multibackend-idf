#include "driver/twai.h"
#include "driver/gpio.h"
#include "init_hardware.h"
#include "esp_log.h"
#if CONFIG_CAN_BACKEND_MCP2515_SINGLE
#include "mcp2515-esp32-idf/mcp2515.h"
#endif
#if CONFIG_CAN_BACKEND_MCP2515_MULTI
#include "mcp2515_multi_adapter.h"
#endif

// Compile-time switch for SPI/link diagnostics in MCP2515 adapter
#ifndef MCP2515_ADAPTER_DEBUG
#define MCP2515_ADAPTER_DEBUG 1
#endif

void init_hardware(can_config_t *hw_config_ptr)
{
#if CONFIG_CAN_BACKEND_TWAI
    // init TWAI controller
    ESP_LOGI("init_hardware", "Adapter: TWAI (builtin)");
    static const gpio_num_t TX_GPIO = GPIO_NUM_39;
    static const gpio_num_t RX_GPIO = GPIO_NUM_40;
    static const uint32_t TX_QUEUE_LEN = 20;
    static const uint32_t RX_QUEUE_LEN = 20;

    *hw_config_ptr = (can_config_t){
        .general_config = {
            .controller_id = 0,
            .mode = TWAI_MODE_NORMAL,
            .tx_io = TX_GPIO, // GPIO 39
            .rx_io = RX_GPIO, // GPIO 40
            .clkout_io = TWAI_IO_UNUSED,
            .bus_off_io = TWAI_IO_UNUSED,
            .tx_queue_len = TX_QUEUE_LEN,
            .rx_queue_len = RX_QUEUE_LEN,
            .alerts_enabled = TWAI_ALERT_NONE, // TWAI_ALERT_RX_DATA | TWAI_ALERT_RX_FIFO_OVERRUN,
            .clkout_divider = 0,
            .intr_flags = ESP_INTR_FLAG_LEVEL1,
            .general_flags = {0}
        },
        .timing_config = TWAI_TIMING_CONFIG_1MBITS(),     // baudrate 1 Mbps
        .filter_config = TWAI_FILTER_CONFIG_ACCEPT_ALL(), // accept all messages (not used for sending)
        .receive_timeout = pdMS_TO_TICKS(100),            // in ms
        .transmit_timeout = pdMS_TO_TICKS(100),           // in ms
        .bus_off_timeout = pdMS_TO_TICKS(1000),           // in ms
        .bus_not_running_timeout = pdMS_TO_TICKS(100),    // in ms
    };

#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    ESP_LOGI("init_hardware", "Adapter: MCP2515_SINGLE");
    // init MCP2515 controller
    static const gpio_num_t MISO_GPIO = GPIO_NUM_37;  // SPI MISO
    static const gpio_num_t MOSI_GPIO = GPIO_NUM_38;  // SPI MOSI
    static const gpio_num_t SCLK_GPIO = GPIO_NUM_36;  // SPI SCLK
    static const gpio_num_t CS_GPIO = GPIO_NUM_33;    // Chip Select
    static const gpio_num_t INT_GPIO = GPIO_NUM_34;   // Interrupt
    static const CAN_SPEED_t CAN_BAUDRATE = CAN_1000KBPS;     // 1 Mbps
    static const CAN_CLOCK_t CAN_CLOCK = MCP_16MHZ;
    static const spi_host_device_t SPI_HOST = SPI2_HOST;  // Explicitly define SPI host
    static const bool USE_LOOPBACK = false;  // Use loopback mode for testing
    static const bool ENABLE_DEBUG_SPI = (MCP2515_ADAPTER_DEBUG != 0);

    *hw_config_ptr = (can_config_t){
        .spi_bus = {
            .miso_io_num = MISO_GPIO,
            .mosi_io_num = MOSI_GPIO,
            .sclk_io_num = SCLK_GPIO,
            .quadwp_io_num = -1,
            .quadhd_io_num = -1,
            .max_transfer_sz = 0,        // No limit on transfer size
            .flags = SPICOMMON_BUSFLAG_MASTER // Enable DMA
        },
        .spi_dev = {
            .mode = 0,                  // SPI mode 0 (CPOL=0, CPHA=0)
            .clock_speed_hz = 10000000, // 10 MHz (40 MHz was before)
            .spics_io_num = CS_GPIO,
            .queue_size = 1024,         // Increased queue size
            .flags = 0,
            .command_bits = 0,
            .address_bits = 0,
            .dummy_bits = 0
        },
        .int_pin = INT_GPIO,
        .can_speed = CAN_BAUDRATE,
        .can_clock = CAN_CLOCK,
        .spi_host = SPI_HOST,            // Add SPI host to config
        .use_loopback = USE_LOOPBACK,
        .enable_debug_spi = ENABLE_DEBUG_SPI
    };

#elif CONFIG_CAN_BACKEND_MCP2515_MULTI 
    ESP_LOGI("init_hardware", "Adapter: MCP2515_MULTI (single-instance test)");
    // Prepare configuration for one instance; actual init is done in canif_init()
    *hw_config_ptr = (can_config_t){
        .host = SPI2_HOST,
        .bus_cfg = {
            .miso_io_num = GPIO_NUM_37,
            .mosi_io_num = GPIO_NUM_38,
            .sclk_io_num = GPIO_NUM_36,
            .quadwp_io_num = -1,
            .quadhd_io_num = -1,
        },
        .dev_cfg = {
            .mode = 0,
            .clock_speed_hz = 10000000,
            .spics_io_num = GPIO_NUM_33,
            .queue_size = 64,
            .flags = 0,
            .command_bits = 0,
            .address_bits = 0,
            .dummy_bits = 0,
        },
        .int_gpio = GPIO_NUM_34,
        .can_speed = CAN_1000KBPS,
        .can_clock = MCP_16MHZ,
    };
#elif CONFIG_CAN_BACKEND_ARDUINO
    // init Arduino driver
#endif
}