#pragma once

#include "driver/gpio.h"
#include "driver/spi_master.h"

// ----- Configuration for SPI wiring and parameters -----

// SPI wiring configuration
typedef struct { 
    gpio_num_t miso_io_num;           // GPIO pin for MISO signal
    gpio_num_t mosi_io_num;           // GPIO pin for MOSI signal
    gpio_num_t sclk_io_num;           // GPIO pin for SCLK (clock) signal
    
} spi_bus_wiring_config_t;

// SPI parameters configuration
typedef struct {
    spi_host_device_t host;    // SPI host device
    int quadwp_io_num;         // GPIO pin for WP (Write Protect) signal in Quad SPI, or -1 if not used
    int quadhd_io_num;         // GPIO pin for HD (Hold) signal in Quad SPI, or -1 if not used
    int max_transfer_sz;       // Maximum transfer size in bytes, 0 for default (4096 bytes)
    uint32_t flags;            // Bus configuration flags (SPICOMMON_BUSFLAG_*)
    int intr_flags;            // Interrupt allocation flags (ESP_INTR_FLAG_*)
    int isr_cpu_id;            // Select which CPU the SPI interrupt is allocated on (INTR_CPU_ID_AUTO)
} spi_bus_params_config_t;


// Full SPI bus configuration in previous notation 
typedef struct {
    spi_bus_wiring_config_t wiring_cfg;
    spi_bus_params_config_t params_cfg;
} spi_bus_parts_config_t;

// All paremeters for SPI bus are in spi_bus_config_t from driver/spi_master.h
// Convert configuration in parts notation for SPI bus to standard spi_bus_config_t.
spi_bus_config_t* convert_spi_bus_parts_to_standard(spi_bus_parts_config_t *parts_cfg);


// ----- Configuration for wiring, connection and parameters for MCP2515 device -----

// --- SPI device wiring configuration ---
typedef struct {
    gpio_num_t cs_gpio;        // GPIO pin for CS signal
    gpio_num_t int_gpio;       // GPIO pin for INT signal
} spi_device_wifing_config_t;

typedef struct {
    CAN_CLOCK_t crystal_frequency;     // Crystal frequency (MCP2515 crystal frequency)
} mcp2515_hardware_config_t;

typedef struct {
    CAN_SPEED_t can_speed;     // CAN speed (CAN clock speed)
    mode_t mode;               // SPI mode
    uint32_t clock_speed_hz;   // Clock speed in Hz (SPI clock speed)
    uint32_t queue_size;       // Queue size
    uint32_t flags;            // Bus configuration flags (SPICOMMON_BUSFLAG_*)
    uint32_t command_bits;     // Command bits
    uint32_t address_bits;     // Address bits
    uint32_t dummy_bits;       // Dummy bits
} spi_device_connection_config_t;

typedef struct {
    spi_device_wifing_config_t wiring_cfg;
    mcp2515_hardware_config_t hardware_cfg;
    spi_device_connection_config_t connection_cfg;
} mcp2515_device_config_t;

// Function to fill the mcp2515_device_config_t struct
mcp2515_device_config_t* fill_mcp2515_device_config(
    mcp2515_device_config_t *device_cfg, 
    spi_device_wifing_config_t *wiring_cfg, 
    mcp2515_hardware_config_t *hardware_cfg, 
    spi_device_connection_config_t *connection_cfg
);

// Configuration for one SPI bus with several MCP2515 devices
typedef struct {
    spi_bus_parts_config_t bus_cfg;
    mcp2515_device_config_t mcp2515_cfg[]; // array of configurations for MCP2515 devices
    size_t mcp2515_count;                // number of MCP2515 devices
} spi_with_several_mcp2515_devices_config_t;

// --- Configuration for several SPI buses with several MCP2515 devices ---
typedef struct {
    spi_with_several_mcp2515_devices_config_t * cfg[]; // array of configurations for SPI buses
    size_t count;  // number of SPI buses
} spi_with_several_mcp2515_devices_config_t;

// --- Configured handels for SPI bus with several MCP2515 devices ---
typedef struct {
    MCP2515_Handle *handle;
    size_t count;
} mcp2515_multi_handle_t;

// Configured handels for more SPI buses with several MCP2515 devices
typedef struct {
    mcp2515_multi_handle_t *handle;
    size_t count;
} mcp2515_multi_handles_t;

// --- Create configured handels for SPI bus with several MCP2515 devices ---
void create_mcp2515_multi_handles(mcp2515_multi_handles_t *handles, spi_with_several_mcp2515_devices_config_t *config);

// --- Create configured handels for more SPI buses with several MCP2515 devices ---
void create_mcp2515_multi_handles(mcp2515_multi_handles_t *handles, spi_with_several_mcp2515_devices_config_t *config);