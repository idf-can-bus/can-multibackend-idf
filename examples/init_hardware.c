// Core includes
#include "driver/twai.h"
#include "driver/gpio.h"
#include "init_hardware.h"
#include "esp_log.h"

// Backend-specific includes
#if CONFIG_CAN_BACKEND_MCP2515_SINGLE
#include "mcp2515_single_adapter.h"  // for debug macro and types
#include "mcp2515-esp32-idf/mcp2515.h"
#endif
#if CONFIG_CAN_BACKEND_MCP2515_MULTI
#include "mcp2515_multi_adapter.h"
#endif

// ---------- TWAI helper ----------
#if CONFIG_CAN_BACKEND_TWAI
static void configure_twai(can_config_t *hw_config_ptr)
{
    ESP_LOGI("init_hardware", "Adapter: TWAI (builtin)");
    static const gpio_num_t TX_GPIO = GPIO_NUM_39;
    static const gpio_num_t RX_GPIO = GPIO_NUM_40;
    static const uint32_t TX_QUEUE_LEN = 20;
    static const uint32_t RX_QUEUE_LEN = 20;

    *hw_config_ptr = (can_config_t){0};
    hw_config_ptr->instance_count = 1;
    hw_config_ptr->twai = (twai_config_t){
        .general_config = {
            .controller_id = 0,
            .mode = TWAI_MODE_NORMAL,
            .tx_io = TX_GPIO,
            .rx_io = RX_GPIO,
            .clkout_io = TWAI_IO_UNUSED,
            .bus_off_io = TWAI_IO_UNUSED,
            .tx_queue_len = TX_QUEUE_LEN,
            .rx_queue_len = RX_QUEUE_LEN,
            .alerts_enabled = TWAI_ALERT_NONE,
            .clkout_divider = 0,
            .intr_flags = ESP_INTR_FLAG_LEVEL1,
            .general_flags = (twai_general_config_t){0}.general_flags
        },
        .timing_config = TWAI_TIMING_CONFIG_1MBITS(),
        .filter_config = TWAI_FILTER_CONFIG_ACCEPT_ALL(),
        .receive_timeout = pdMS_TO_TICKS(100),
        .transmit_timeout = pdMS_TO_TICKS(100),
        .bus_off_timeout = pdMS_TO_TICKS(1000),
        .bus_not_running_timeout = pdMS_TO_TICKS(100),
    };
}
#endif // CONFIG_CAN_BACKEND_TWAI

// ---------- MCP2515 single helper ----------
#if CONFIG_CAN_BACKEND_MCP2515_SINGLE
static void configure_mcp2515_single(can_config_t *hw_config_ptr)
{
    ESP_LOGI("init_hardware", "Adapter: MCP2515_SINGLE");

    static const gpio_num_t MISO_GPIO = GPIO_NUM_37;
    static const gpio_num_t MOSI_GPIO = GPIO_NUM_38;
    static const gpio_num_t SCLK_GPIO = GPIO_NUM_36;
    static const gpio_num_t CS_GPIO   = GPIO_NUM_33;
    static const gpio_num_t INT_GPIO  = GPIO_NUM_34;
    static const CAN_SPEED_t CAN_BAUDRATE = CAN_1000KBPS;
    static const CAN_CLOCK_t CAN_CLOCK     = MCP_16MHZ;
    static const spi_host_device_t SPI_HOST = SPI2_HOST;
    static const bool USE_LOOPBACK = false;
    #if MCP2515_ADAPTER_DEBUG
    static const bool ENABLE_DEBUG_SPI = true;
    #else
    static const bool ENABLE_DEBUG_SPI = false;
    #endif

    *hw_config_ptr = (can_config_t){0};
    hw_config_ptr->instance_count = 1;
    hw_config_ptr->single = (mcp2515_single_config_t){
        .spi_bus = {
            .miso_io_num = MISO_GPIO,
            .mosi_io_num = MOSI_GPIO,
            .sclk_io_num = SCLK_GPIO,
            .quadwp_io_num = -1,
            .quadhd_io_num = -1,
            .max_transfer_sz = 0,
            .flags = SPICOMMON_BUSFLAG_MASTER
        },
        .spi_dev = {
            .mode = 0,
            .clock_speed_hz = 10000000,
            .spics_io_num = CS_GPIO,
            .queue_size = 1024,
            .flags = 0,
            .command_bits = 0,
            .address_bits = 0,
            .dummy_bits = 0
        },
        .int_pin = INT_GPIO,
        .can_speed = CAN_BAUDRATE,
        .can_clock = CAN_CLOCK,
        .spi_host = SPI_HOST,
        .use_loopback = USE_LOOPBACK,
        .enable_debug_spi = ENABLE_DEBUG_SPI
    };
}
#endif // CONFIG_CAN_BACKEND_MCP2515_SINGLE

// ---------- MCP2515 multi helpers ----------
#if CONFIG_CAN_BACKEND_MCP2515_MULTI
static void configure_mcp2515_multi_send(can_config_t *hw_config_ptr)
{
    ESP_LOGI("init_hardware", "Adapter: MCP2515_MULTI (send bundle)");
    *hw_config_ptr = (can_config_t){0};
    hw_config_ptr->instance_count = 1;
    hw_config_ptr->multi = (mcp_multi_bundle_cfg_t){
        .instances = {
            (mcp_multi_instance_cfg_t){
                .host = SPI2_HOST,
                .bus_cfg = {
                    .miso_io_num = GPIO_NUM_15,
                    .mosi_io_num = GPIO_NUM_16,
                    .sclk_io_num = GPIO_NUM_14,
                    .quadwp_io_num = -1,
                    .quadhd_io_num = -1,
                },
                .dev_cfg = {
                    .mode = 0,
                    .clock_speed_hz = 10000000,
                    .spics_io_num = GPIO_NUM_11,
                    .queue_size = 64,
                    .flags = 0,
                    .command_bits = 0,
                    .address_bits = 0,
                    .dummy_bits = 0,
                },
            }
        }
    };
}

static void configure_mcp2515_multi_receive(can_config_t *hw_config_ptr)
{
    ESP_LOGI("init_hardware", "Adapter: MCP2515_MULTI (receive bundle)");
    *hw_config_ptr = (can_config_t){0};
    mcp_multi_instance_cfg_t tmp[] = {
        (mcp_multi_instance_cfg_t){
            .host = SPI1_HOST,
            .bus_cfg = {
                .miso_io_num = GPIO_NUM_15,
                .mosi_io_num = GPIO_NUM_16,
                .sclk_io_num = GPIO_NUM_14,
                .quadwp_io_num = -1,
                .quadhd_io_num = -1,
            },
            .dev_cfg = {
                .mode = 0,
                .clock_speed_hz = 10000000,
                .spics_io_num = GPIO_NUM_33,   // CS A
                .queue_size = 64,
                .flags = 0,
                .command_bits = 0,
                .address_bits = 0,
                .dummy_bits = 0,
            },
            .int_gpio = GPIO_NUM_34,
            .can_speed = CAN_1000KBPS,
            .can_clock = MCP_16MHZ,
        },
        (mcp_multi_instance_cfg_t){
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
                .spics_io_num = GPIO_NUM_35,   // CS B
                .queue_size = 64,
                .flags = 0,
                .command_bits = 0,
                .address_bits = 0,
                .dummy_bits = 0,
            },
            .int_gpio = GPIO_NUM_39,
            .can_speed = CAN_1000KBPS,
            .can_clock = MCP_16MHZ,
        },
        (mcp_multi_instance_cfg_t){
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
                .spics_io_num = GPIO_NUM_40,   // CS C
                .queue_size = 64,
                .flags = 0,
                .command_bits = 0,
                .address_bits = 0,
                .dummy_bits = 0,
            },
            .int_gpio = GPIO_NUM_12,
            .can_speed = CAN_1000KBPS,
            .can_clock = MCP_16MHZ,
        }
    };

    hw_config_ptr->instance_count = sizeof(tmp)/sizeof(tmp[0]);
    hw_config_ptr->multi.instance_count = hw_config_ptr->instance_count;
    for (size_t i=0; i<hw_config_ptr->multi.instance_count; ++i) {
        hw_config_ptr->multi.instances[i] = tmp[i];
    }
}
#endif

// ---------- Dispatcher ----------
static void configure_hardware(can_config_t *hw_config_ptr)
{
#if CONFIG_CAN_BACKEND_TWAI
    configure_twai(hw_config_ptr);
#elif CONFIG_CAN_BACKEND_MCP2515_SINGLE
    configure_mcp2515_single(hw_config_ptr);
#elif CONFIG_CAN_BACKEND_MCP2515_MULTI
  #if EXAMPLE_SEND_MULTI
    configure_mcp2515_multi_send(hw_config_ptr);
  #elif EXAMPLE_RECV_POLL_MULTI || EXAMPLE_RECV_INT_MULTI
    configure_mcp2515_multi_receive(hw_config_ptr);
  #else
    ESP_LOGW("init_hardware", "MCP2515_MULTI selected but no example variant defined");
  #endif
#elif CONFIG_CAN_BACKEND_ARDUINO
    ESP_LOGW("init_hardware", "Arduino backend not implemented");
#else
    ESP_LOGE("init_hardware", "No CAN backend selected");
#endif
}

void init_hardware(can_config_t *hw_config_ptr)
{
    configure_hardware(hw_config_ptr);
    (void)canif_init(hw_config_ptr);
}


