#pragma once

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "components/can_backend_mcp2515_single/mcp2515-esp32-idf/mcp2515.h"

#ifdef __cplusplus
extern "C" {
#endif

// ---------- SPI BUS (wiring + params) ----------
typedef struct {
    gpio_num_t miso_io_num;
    gpio_num_t mosi_io_num;
    gpio_num_t sclk_io_num;
    int        quadwp_io_num;  // -1 if unused
    int        quadhd_io_num;  // -1 if unused
} mcp_spi_bus_wiring_t;

typedef struct {
    spi_host_device_t host;      // SPIx_HOST
    int               max_transfer_sz; // 0 = default
    uint32_t          flags;     // SPICOMMON_BUSFLAG_*
    int               dma_chan;  // SPI_DMA_CH_AUTO or specific
    int               intr_flags;   // optional
    int               isr_cpu_id;   // optional
} mcp_spi_bus_params_t;

typedef struct {
    mcp_spi_bus_wiring_t wiring;
    mcp_spi_bus_params_t params;
    bool                 manage_bus_lifetime;
} mcp_spi_bus_config_t;

static inline bool mcp_spi_bus_to_idf(const mcp_spi_bus_config_t *src,
                                      spi_host_device_t *out_host,
                                      spi_bus_config_t *out_bus_cfg,
                                      int *out_dma_chan)
{
    if (!src || !out_host || !out_bus_cfg || !out_dma_chan) return false;
    *out_host = src->params.host;
    *out_dma_chan = src->params.dma_chan;
    out_bus_cfg->miso_io_num = src->wiring.miso_io_num;
    out_bus_cfg->mosi_io_num = src->wiring.mosi_io_num;
    out_bus_cfg->sclk_io_num = src->wiring.sclk_io_num;
    out_bus_cfg->quadwp_io_num = src->wiring.quadwp_io_num;
    out_bus_cfg->quadhd_io_num = src->wiring.quadhd_io_num;
    out_bus_cfg->max_transfer_sz = src->params.max_transfer_sz;
    out_bus_cfg->flags = src->params.flags;
    return true;
}

// ---------- SPI DEVICE (wiring + params) ----------
typedef struct {
    gpio_num_t cs_gpio;
    gpio_num_t int_gpio;   // GPIO_NUM_NC if unused
    gpio_num_t stby_gpio;  // optional, GPIO_NUM_NC if unused
    gpio_num_t rst_gpio;   // optional, GPIO_NUM_NC if unused
} mcp_spi_dev_wiring_t;

typedef struct {
    uint8_t   mode;             // 0..3
    uint32_t  clock_speed_hz;   // e.g., 10 MHz
    uint32_t  queue_size;       // e.g., 64/1024
    uint32_t  flags;
    uint32_t  command_bits;
    uint32_t  address_bits;
    uint32_t  dummy_bits;
} mcp_spi_dev_params_t;

static inline void mcp_spi_dev_to_idf(const mcp_spi_dev_wiring_t *w,
                                      const mcp_spi_dev_params_t *p,
                                      spi_device_interface_config_t *out)
{
    out->mode = p->mode;
    out->clock_speed_hz = p->clock_speed_hz;
    out->spics_io_num = w->cs_gpio;
    out->queue_size = p->queue_size;
    out->flags = p->flags;
    out->command_bits = p->command_bits;
    out->address_bits = p->address_bits;
    out->dummy_bits = p->dummy_bits;
}

// ---------- MCP2515 device (HW + CAN params) ----------
typedef struct {
    CAN_CLOCK_t crystal_frequency;   // MCP_8MHZ / MCP_16MHZ / MCP_20MHZ
} mcp2515_hw_t;

typedef struct {
    CAN_SPEED_t can_speed;      // CAN_500KBPS, CAN_1000KBPS, ...
    bool        use_loopback;   // optional test mode
} mcp2515_can_params_t;

typedef struct {
    mcp_spi_dev_wiring_t   wiring;
    mcp_spi_dev_params_t   spi_params;
    mcp2515_hw_t           hw;
    mcp2515_can_params_t   can;
} mcp2515_device_config_t;

// Bundle: one SPI bus with multiple MCP2515 devices
typedef struct {
    mcp_spi_bus_config_t       bus;
    const mcp2515_device_config_t *devices;
    size_t                     device_count;
} mcp2515_bundle_config_t;

#ifdef __cplusplus
}
#endif


