#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

// --------------------------------------------------------------------------------------
// Public types

typedef enum {
    MCP_20MHZ,
    MCP_16MHZ,
    MCP_8MHZ
} CAN_CLOCK_t;

typedef enum {
    CAN_5KBPS,
    CAN_10KBPS,
    CAN_20KBPS,
    CAN_31K25BPS,
    CAN_33KBPS,
    CAN_40KBPS,
    CAN_50KBPS,
    CAN_80KBPS,
    CAN_83K3BPS,
    CAN_95KBPS,
    CAN_100KBPS,
    CAN_125KBPS,
    CAN_200KBPS,
    CAN_250KBPS,
    CAN_500KBPS,
    CAN_1000KBPS
} CAN_SPEED_t;

typedef enum {
    ERROR_OK        = 0,
    ERROR_FAIL      = 1,
    ERROR_ALLTXBUSY = 2,
    ERROR_FAILINIT  = 3,
    ERROR_FAILTX    = 4,
    ERROR_NOMSG     = 5
} ERROR_t;

typedef struct MCP2515_Context* MCP2515_Handle;

typedef struct {
    CAN_SPEED_t can_speed;
    CAN_CLOCK_t can_clock;
} mcp2515_multi_config_t;

// Event mask bits
#define MCP2515_EVENT_RX_READY   (1u << 0)
#define MCP2515_EVENT_ERROR      (1u << 1)

typedef void (*MCP2515_EventCallback)(MCP2515_Handle h, uint32_t eventMask, void* userData);

// Minimal CAN frame used by this library
typedef struct {
    uint32_t can_id;   // includes EFF/RTR bits when used internally
    uint8_t  can_dlc;
    uint8_t  data[8];
} CAN_FRAME;

// --------------------------------------------------------------------------------------
// Creation / destruction

// Create using existing SPI device
ERROR_t MCP2515_CreateOnDevice(spi_device_handle_t spi,
                               gpio_num_t int_gpio,
                               const mcp2515_multi_config_t* cfg,
                               MCP2515_Handle* out_handle);

// Create on SPI bus (idempotent bus init), adds device
ERROR_t MCP2515_CreateOnBus(spi_host_device_t host,
                            const spi_bus_config_t* bus_cfg,
                            const spi_device_interface_config_t* dev_cfg,
                            gpio_num_t int_gpio,
                            const mcp2515_multi_config_t* cfg,
                            MCP2515_Handle* out_handle);

void    MCP2515_Destroy(MCP2515_Handle h);

// SPI helper (optional)
esp_err_t mcp2515_spi_init_bus_if_needed(spi_host_device_t host, const spi_bus_config_t* bus_cfg);
esp_err_t mcp2515_spi_add_device(spi_host_device_t host, const spi_device_interface_config_t* dev_cfg, spi_device_handle_t* out_spi);
esp_err_t mcp2515_spi_remove_device(spi_device_handle_t spi);

// --------------------------------------------------------------------------------------
// Basic control
ERROR_t MCP2515_Reset(MCP2515_Handle h);
ERROR_t MCP2515_SetBitrate(MCP2515_Handle h, CAN_SPEED_t speed, CAN_CLOCK_t clock);
ERROR_t MCP2515_SetNormalMode(MCP2515_Handle h);
ERROR_t MCP2515_SetLoopbackMode(MCP2515_Handle h);

// Tx/Rx
ERROR_t MCP2515_SendMessageAfterCtrlCheck(MCP2515_Handle h, const CAN_FRAME* frame);
ERROR_t MCP2515_ReadMessageAfterStatCheck(MCP2515_Handle h, CAN_FRAME* frame);

// Events
void     MCP2515_SetEventCallback(MCP2515_Handle h, MCP2515_EventCallback cb, void* userData);
uint32_t MCP2515_WaitForEvent(MCP2515_Handle h, uint32_t timeout_ticks);

// Errors
uint8_t MCP2515_GetErrorFlags(MCP2515_Handle h);
void    MCP2515_ClearRXnOVR(MCP2515_Handle h);
void    MCP2515_ClearERRIF(MCP2515_Handle h);

#ifdef __cplusplus
}
#endif


