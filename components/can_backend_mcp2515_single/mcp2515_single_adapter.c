#include "mcp2515_single_adapter.h"
#include "mcp2515-esp32-idf/mcp2515.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include <string.h>
#include <stdlib.h>

static const char *TAG = "MCP2515_SINGLE_ADAPTER";
static mcp2515_single_config_t mcp2515_config;
static volatile bool interrupt_pending = false;

// Interrupt handler
static void IRAM_ATTR isr_handler(void* arg) {
    interrupt_pending = true;
}

// Initialize MCP2515
bool mcp2515_single_init(const mcp2515_single_config_t *cfg) {
    ESP_LOGI(TAG, "Initializing MCP2515 adapter");
    
    // Store configuration
    memcpy(&mcp2515_config, cfg, sizeof(mcp2515_single_config_t));
    
    // Step 1: Initialize MCP2515 chip structure
    ERROR_t ret = MCP2515_init();
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to initialize MCP2515: %d", ret);
        return false;
    }
    
    // Step 2: Initialize SPI bus
    esp_err_t err = spi_bus_initialize(cfg->spi_host, &cfg->spi_bus, SPI_DMA_CH_AUTO);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize SPI bus: %s", esp_err_to_name(err));
        return false;
    }
    
    // Step 3: Add MCP2515 device to SPI bus
    err = spi_bus_add_device(cfg->spi_host, &cfg->spi_dev, &MCP2515_Object->spi);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to add MCP2515 device to SPI bus: %s", esp_err_to_name(err));
        return false;
    }
    
    // Step 4: Reset and configure MCP2515
    ret = MCP2515_reset();
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to reset MCP2515: %d", ret);
        return false;
    }
    
    // Step 5: Set bitrate
    ret = MCP2515_setBitrate(CAN_1000KBPS, MCP_8MHZ);
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to set bitrate: %d", ret);
        return false;
    }
    
    // Step 6: Switch to normal mode
    ret = MCP2515_setNormalMode();
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to set normal mode: %d", ret);
        return false;
    }
    
    // Step 7: Configure interrupts and filters
    MCP2515_setRegister(MCP_CANINTE, CANINTF_RX0IF | CANINTF_RX1IF | CANINTF_ERRIF | CANINTF_MERRF);
    
    // Configure filters to accept all messages
    const RXF_t filters[] = {RXF0, RXF1, RXF2, RXF3, RXF4, RXF5};
    for (int i=0; i<6; i++) {
        ret = MCP2515_setFilter(filters[i], false, 0);  // false = standard frame, 0 = accept all
        if (ret != ERROR_OK) {
            ESP_LOGE(TAG, "Failed to set filter %d: %d", i, ret);
            return false;
        }
    }
    
    // Configure masks to accept all messages
    MASK_t masks[] = {MASK0, MASK1};
    for (int i=0; i<2; i++) {
        ret = MCP2515_setFilterMask(masks[i], false, 0);  // false = standard frame, 0 = accept all
        if (ret != ERROR_OK) {
            ESP_LOGE(TAG, "Failed to set mask %d: %d", i, ret);
            return false;
        }
    }
    
    // Step 8: Configure interrupts
    gpio_config_t io_conf = {
        .pin_bit_mask = 1ULL << cfg->int_pin,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE
    };
    
    err = gpio_config(&io_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure GPIO %d: %s", cfg->int_pin, esp_err_to_name(err));
        return false;
    }
    
    // Step 9: Install ISR service
    err = gpio_install_isr_service(0);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Failed to install ISR service: %s", esp_err_to_name(err));
        return false;
    }
    
    // Step 10: Add interrupt handler
    err = gpio_isr_handler_add(cfg->int_pin, isr_handler, NULL);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to add interrupt handler: %s", esp_err_to_name(err));
        return false;
    }
    
    ESP_LOGI(TAG, "MCP2515 adapter initialized successfully");
    return true;
}

// Deinitialize MCP2515
bool mcp2515_single_deinit() {
    ESP_LOGI(TAG, "Deinitializing MCP2515 adapter");
    
    // Step 1: Switch to config mode
    ERROR_t ret = MCP2515_setConfigMode();
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to set config mode: %d", ret);
        return false;
    }
    
    // Step 2: Remove interrupt handler
    if (mcp2515_config.int_pin >= 0) {
        esp_err_t err = gpio_isr_handler_remove(mcp2515_config.int_pin);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to remove interrupt handler: %s", esp_err_to_name(err));
            return false;
        }
    }
    
    // Step 3: Remove SPI device
    if (MCP2515_Object && MCP2515_Object->spi) {
        esp_err_t err = spi_bus_remove_device(MCP2515_Object->spi);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to remove SPI device: %s", esp_err_to_name(err));
            return false;
        }
    }
    
    // Step 4: Free SPI bus
    esp_err_t err = spi_bus_free(mcp2515_config.spi_host);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to free SPI bus: %s", esp_err_to_name(err));
        return false;
    }
    
    ESP_LOGI(TAG, "MCP2515 adapter deinitialized successfully");
    return true;
}

// Send message
bool mcp2515_single_send(const can_message_t *raw_out_msg) {
    if (raw_out_msg->dlc > CAN_MAX_DLEN) {
        ESP_LOGE(TAG, "Message too long: %d bytes", raw_out_msg->dlc);
        return false;
    }

    CAN_FRAME_t frame;  // Array of size 1 containing can_frame structure
    frame[0].can_id = raw_out_msg->id;
    frame[0].can_dlc = raw_out_msg->dlc;
    memcpy(frame[0].data, raw_out_msg->data, raw_out_msg->dlc);
    
    ERROR_t ret = MCP2515_sendMessageAfterCtrlCheck(frame);
    
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to send message: %d", ret);
        return false;
    }
    
    return true;
}

// Receive message
bool mcp2515_single_receive(can_message_t *raw_in_msg) {
    if (!interrupt_pending && !MCP2515_checkReceive()) {
        return false;
    }
    
    // Check for errors
    if (MCP2515_checkError()) {
        uint8_t eflg = MCP2515_getErrorFlags();
        ESP_LOGE(TAG, "MCP2515 error flags: 0x%02x", eflg);
        MCP2515_clearERRIF();
        return false;
    }
    
    CAN_FRAME_t frame;  // Array of size 1 containing can_frame structure
    ERROR_t ret = MCP2515_readMessageAfterStatCheck(frame);
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to read message: %d", ret);
        return false;
    }
    
    if (frame[0].can_dlc > CAN_MAX_DLEN) {
        ESP_LOGE(TAG, "Received message too long: %d bytes", frame[0].can_dlc);
        return false;
    }
    
    raw_in_msg->id = frame[0].can_id;
    raw_in_msg->dlc = frame[0].can_dlc;
    memcpy(raw_in_msg->data, frame[0].data, frame[0].can_dlc);
    
    interrupt_pending = false;  // Reset interrupt flag after successful read
    return true;
}