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

// Compile-time switch for SPI/link diagnostics in MCP2515 adapter
#ifndef MCP2515_ADAPTER_DEBUG
#define MCP2515_ADAPTER_DEBUG 0
#endif

#if MCP2515_ADAPTER_DEBUG
static void mcp2515_diagnostics(void) {
    ESP_LOGI(TAG, "=== MCP2515 Diagnostics ===");
    
    // Extended SPI Test - try multiple reads/writes
    ESP_LOGI(TAG, "Testing SPI communication...");
    
    // Test 1: Write and read back CNF1 (should be in config mode, so writable)
    uint8_t cnf1_original = MCP2515_readRegister(MCP_CNF1);
    ESP_LOGI(TAG, "CNF1 original: 0x%02X", cnf1_original);
    
    MCP2515_setRegister(MCP_CNF1, 0xAA);
    vTaskDelay(pdMS_TO_TICKS(10));
    uint8_t cnf1_test1 = MCP2515_readRegister(MCP_CNF1);
    ESP_LOGI(TAG, "CNF1 after write 0xAA: 0x%02X %s", cnf1_test1, (cnf1_test1 == 0xAA) ? "OK" : "FAIL");
    
    MCP2515_setRegister(MCP_CNF1, 0x55);
    vTaskDelay(pdMS_TO_TICKS(10));
    uint8_t cnf1_test2 = MCP2515_readRegister(MCP_CNF1);
    ESP_LOGI(TAG, "CNF1 after write 0x55: 0x%02X %s", cnf1_test2, (cnf1_test2 == 0x55) ? "OK" : "FAIL");
    
    // Restore original
    MCP2515_setRegister(MCP_CNF1, cnf1_original);
    
    // Test 2: Read CANSTAT multiple times (should be consistent)
    uint8_t canstat1 = MCP2515_readRegister(MCP_CANSTAT);
    uint8_t canstat2 = MCP2515_readRegister(MCP_CANSTAT);
    uint8_t canstat3 = MCP2515_readRegister(MCP_CANSTAT);
    ESP_LOGI(TAG, "CANSTAT reads: 0x%02X, 0x%02X, 0x%02X %s", 
             canstat1, canstat2, canstat3,
             (canstat1 == canstat2 && canstat2 == canstat3) ? "Consistent" : "INCONSISTENT!");
    
    if (canstat1 == 0xFF || canstat1 == 0x00) {
        ESP_LOGE(TAG, "SPI appears disconnected (all 0xFF or 0x00)");
    }
    
    uint8_t canstat = MCP2515_readRegister(MCP_CANSTAT);
    uint8_t canctrl = MCP2515_readRegister(MCP_CANCTRL);
    uint8_t eflg = MCP2515_readRegister(MCP_EFLG);
    uint8_t canintf = MCP2515_readRegister(MCP_CANINTF);
    uint8_t tec = MCP2515_readRegister(MCP_TEC);
    uint8_t rec = MCP2515_readRegister(MCP_REC);
    uint8_t cnf1 = MCP2515_readRegister(MCP_CNF1);
    uint8_t cnf2 = MCP2515_readRegister(MCP_CNF2);
    uint8_t cnf3 = MCP2515_readRegister(MCP_CNF3);
    
    ESP_LOGI(TAG, "CANSTAT:  0x%02X (Mode: %d)", canstat, (canstat >> 5) & 0x07);
    ESP_LOGI(TAG, "CANCTRL:  0x%02X", canctrl);
    ESP_LOGI(TAG, "EFLG:     0x%02X", eflg);
    ESP_LOGI(TAG, "CANINTF:  0x%02X", canintf);
    ESP_LOGI(TAG, "TEC:      %d", tec);
    ESP_LOGI(TAG, "REC:      %d", rec);
    ESP_LOGI(TAG, "CNF1:     0x%02X", cnf1);
    ESP_LOGI(TAG, "CNF2:     0x%02X", cnf2);
    ESP_LOGI(TAG, "CNF3:     0x%02X", cnf3);
    ESP_LOGI(TAG, "========================");
}
#endif

// Interrupt handler
static void IRAM_ATTR isr_handler(void* arg) {
    interrupt_pending = true;
}

// test GPIO Configuration (CS pin)
#if MCP2515_ADAPTER_DEBUG
static void test_gpio_configuration(const mcp2515_single_config_t *cfg) {
     // Test CS pin manually
     gpio_config_t cs_test = {
        .pin_bit_mask = (1ULL << cfg->spi_dev.spics_io_num),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    ESP_LOGI(TAG, "Testing GPIO Configuration.");
    gpio_config(&cs_test);
    
    ESP_LOGI(TAG, "Testing CS pin (GPIO %d)", cfg->spi_dev.spics_io_num);
    gpio_set_level(cfg->spi_dev.spics_io_num, 1);  // High
    vTaskDelay(pdMS_TO_TICKS(100));
    ESP_LOGI(TAG, "CS HIGH - measure voltage on CS pin now");
    gpio_set_level(cfg->spi_dev.spics_io_num, 0);  // Low
    vTaskDelay(pdMS_TO_TICKS(100));
    ESP_LOGI(TAG, "CS LOW - measure voltage on CS pin now");
    gpio_set_level(cfg->spi_dev.spics_io_num, 1);  // Back to high
}
#endif


// Initialize MCP2515
bool mcp2515_single_init(const mcp2515_single_config_t *cfg) {
    ESP_LOGI(TAG, "Initializing MCP2515 adapter");
    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        test_gpio_configuration(cfg);
    }
    #endif

    // Store configuration
    memcpy(&mcp2515_config, cfg, sizeof(mcp2515_single_config_t));
    
    // Step 1: Initialize MCP2515 chip structure
    ERROR_t ret = MCP2515_init();
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to initialize MCP2515: %d", ret);
        return false;
    }
    
    // Step 2: Initialize SPI bus
    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        ESP_LOGI("HARDWARE", "GPIO Configuration:");
        ESP_LOGI("HARDWARE", "  MISO: GPIO_%d", cfg->spi_bus.miso_io_num);
        ESP_LOGI("HARDWARE", "  MOSI: GPIO_%d", cfg->spi_bus.mosi_io_num);
        ESP_LOGI("HARDWARE", "  SCLK: GPIO_%d", cfg->spi_bus.sclk_io_num);
        ESP_LOGI("HARDWARE", "  CS:   GPIO_%d", cfg->spi_dev.spics_io_num);
        ESP_LOGI("HARDWARE", "  INT:  GPIO_%d", cfg->int_pin);
    }
    #endif
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
    ESP_LOGI(TAG, "Setting bitrate: speed=%d, clock=%d", cfg->can_speed, cfg->can_clock);
    ret = MCP2515_setBitrate(cfg->can_speed, cfg->can_clock);
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to set bitrate: %d", ret);
        return false;
    }
    ESP_LOGI(TAG, "Bitrate set successfully");

    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        // Enable CLKOUT for diagnostics (verifies oscillator is running)
        ESP_LOGI(TAG, "Enabling CLKOUT for diagnostics");
        MCP2515_setClkOut(CLKOUT_DIV1);
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    #endif

    // Step 6: Switch to normal mode or loopback mode with detailed diagnostics
    CANCTRL_REQOP_MODE_t target_mode;
    #if MCP2515_ADAPTER_DEBUG
    const char* mode_name;
    #endif

    if (cfg->use_loopback) {
        target_mode = CANCTRL_REQOP_LOOPBACK;
        #if MCP2515_ADAPTER_DEBUG
        mode_name = "loopback";
        #endif
    } else {
        target_mode = CANCTRL_REQOP_NORMAL;
        #if MCP2515_ADAPTER_DEBUG
        mode_name = "normal";
        #endif
    }

    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        ESP_LOGI(TAG, "Attempting to switch to %s mode (0x%02X)", mode_name, target_mode);
    }
    #endif

    // Read current state BEFORE attempting change
    #if MCP2515_ADAPTER_DEBUG
    uint8_t canstat_before = MCP2515_readRegister(MCP_CANSTAT);
    uint8_t canctrl_before = MCP2515_readRegister(MCP_CANCTRL);
    if (cfg->enable_debug_spi) {
        ESP_LOGI(TAG, "BEFORE: CANSTAT=0x%02X (mode=%d), CANCTRL=0x%02X",
                 canstat_before, (canstat_before >> 5) & 0x07, canctrl_before);
    }
    #endif

    // Request mode change
    MCP2515_modifyRegister(MCP_CANCTRL, CANCTRL_REQOP, target_mode);
    vTaskDelay(pdMS_TO_TICKS(20));

    // Check if mode changed - try multiple times with detailed logging
    bool mode_ok = false;
    for (int attempt = 0; attempt < 10; attempt++) {
        uint8_t canstat = MCP2515_readRegister(MCP_CANSTAT);
        uint8_t current_mode = (canstat >> 5) & 0x07;
        uint8_t requested_mode = (target_mode >> 5) & 0x07;

        #if MCP2515_ADAPTER_DEBUG
        uint8_t canctrl = MCP2515_readRegister(MCP_CANCTRL);
        if (cfg->enable_debug_spi) {
            ESP_LOGI(TAG, "  Attempt %d: CANSTAT=0x%02X (mode=%d), CANCTRL=0x%02X (want mode=%d)",
                     attempt, canstat, current_mode, canctrl, requested_mode);
        }
        #endif

        if (current_mode == requested_mode) {
            #if MCP2515_ADAPTER_DEBUG
            if (cfg->enable_debug_spi) {
                ESP_LOGI(TAG, "  SUCCESS! Mode changed to %d", current_mode);
            }
            #endif
            mode_ok = true;
            break;
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }

    if (!mode_ok) {
        #if MCP2515_ADAPTER_DEBUG
        if (cfg->enable_debug_spi) {
            ESP_LOGE(TAG, "FAILED to set %s mode after 10 attempts!", mode_name);
        }
        #endif

        // Read all relevant registers for debugging
        #if MCP2515_ADAPTER_DEBUG
        uint8_t canstat = MCP2515_readRegister(MCP_CANSTAT);
        uint8_t canctrl = MCP2515_readRegister(MCP_CANCTRL);
        uint8_t cnf1 = MCP2515_readRegister(MCP_CNF1);
        uint8_t cnf2 = MCP2515_readRegister(MCP_CNF2);
        uint8_t cnf3 = MCP2515_readRegister(MCP_CNF3);
        if (cfg->enable_debug_spi) {
            ESP_LOGE(TAG, "Final registers:");
            ESP_LOGE(TAG, "  CANSTAT: 0x%02X (mode=%d)", canstat, (canstat >> 5) & 0x07);
            ESP_LOGE(TAG, "  CANCTRL: 0x%02X", canctrl);
            ESP_LOGE(TAG, "  CNF1:    0x%02X", cnf1);
            ESP_LOGE(TAG, "  CNF2:    0x%02X", cnf2);
            ESP_LOGE(TAG, "  CNF3:    0x%02X", cnf3);
        }
        #endif

        return false;
    }
    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        ESP_LOGI(TAG, "Mode successfully set to %s", mode_name);
    }
    #endif

    // Wait a bit and verify mode is stable
    vTaskDelay(pdMS_TO_TICKS(50));
    uint8_t canstat_after = MCP2515_readRegister(MCP_CANSTAT);
    uint8_t final_mode = (canstat_after >> 5) & 0x07;
    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        ESP_LOGI(TAG, "Mode stability check: CANSTAT=0x%02X (mode=%d)", canstat_after, final_mode);
    }
    #endif
    if (final_mode != ((target_mode >> 5) & 0x07)) {
        ESP_LOGE(TAG, "WARNING: Mode changed back! Expected %d, got %d",
                 (target_mode >> 5) & 0x07, final_mode);
        return false;
    }
    
    // Step 7: Configure interrupts and filters
    // Enable RXnIF and ERRIF; do not enable MERRF to reduce spurious error interrupts on heavy traffic
    MCP2515_setRegister(MCP_CANINTE, CANINTF_RX0IF | CANINTF_RX1IF | CANINTF_ERRIF);
    
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

    // Re-apply requested mode after filter/mask configuration (they force config mode)
    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        ESP_LOGI(TAG, "Re-applying %s mode after filter/mask configuration", mode_name);
    }
    #endif
    MCP2515_modifyRegister(MCP_CANCTRL, CANCTRL_REQOP, target_mode);
    vTaskDelay(pdMS_TO_TICKS(20));
    bool mode2_ok = false;
    for (int attempt = 0; attempt < 10; attempt++) {
        uint8_t canstat = MCP2515_readRegister(MCP_CANSTAT);
        uint8_t current_mode = (canstat >> 5) & 0x07;
        uint8_t requested_mode = (target_mode >> 5) & 0x07;
        #if MCP2515_ADAPTER_DEBUG
        if (cfg->enable_debug_spi) {
            ESP_LOGI(TAG, "  Re-apply attempt %d: CANSTAT=0x%02X (mode=%d), want mode=%d",
                     attempt, canstat, current_mode, requested_mode);
        }
        #endif
        if (current_mode == requested_mode) {
            mode2_ok = true;
            break;
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
    if (!mode2_ok) {
        #if MCP2515_ADAPTER_DEBUG
        if (cfg->enable_debug_spi) {
            ESP_LOGE(TAG, "Failed to re-apply %s mode after filter/mask configuration", mode_name);
        }
        #endif
        return false;
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
    #if MCP2515_ADAPTER_DEBUG
    if (cfg->enable_debug_spi) {
        mcp2515_diagnostics();
    }
    #endif
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

    // Check TX buffer status BEFORE sending
    uint8_t ctrl0 = MCP2515_readRegister(MCP_TXB0CTRL);
    uint8_t ctrl1 = MCP2515_readRegister(MCP_TXB1CTRL);
    uint8_t ctrl2 = MCP2515_readRegister(MCP_TXB2CTRL);
    ESP_LOGD(TAG, "TX buffer status: TXB0=0x%02X, TXB1=0x%02X, TXB2=0x%02X", ctrl0, ctrl1, ctrl2);
 

    CAN_FRAME_t frame;  // Array of size 1 containing can_frame structure
    frame[0].can_id = raw_out_msg->id;
    frame[0].can_dlc = raw_out_msg->dlc;
    memcpy(frame[0].data, raw_out_msg->data, raw_out_msg->dlc);
    
    ERROR_t ret = MCP2515_sendMessageAfterCtrlCheck(frame);
    
    if (ret != ERROR_OK) {
        // Read error flags
        uint8_t eflg = MCP2515_readRegister(MCP_EFLG);
        uint8_t canintf = MCP2515_readRegister(MCP_CANINTF);
        // Read TX buffer CTRL registers to diagnose reason
        uint8_t t0 = MCP2515_readRegister(MCP_TXB0CTRL);
        uint8_t t1 = MCP2515_readRegister(MCP_TXB1CTRL);
        uint8_t t2 = MCP2515_readRegister(MCP_TXB2CTRL);
        ESP_LOGE(TAG, "Failed to send message: %d, EFLG=0x%02X, CANINTF=0x%02X", ret, eflg, canintf);
        ESP_LOGE(TAG, "TXBCTRL: TXB0=0x%02X TXB1=0x%02X TXB2=0x%02X", t0, t1, t2);
        ESP_LOGE(TAG, "TXB0 flags: ABTF=%d MLOA=%d TXERR=%d", (t0 & TXB_ABTF)?1:0, (t0 & TXB_MLOA)?1:0, (t0 & TXB_TXERR)?1:0);
        // Clear message error flag if set
        if (canintf & CANINTF_MERRF) {
            MCP2515_clearMERR();
        }
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
        // Handle RX buffer overrun explicitly: clear EFLG RXnOVR and related interrupts
        if (eflg & (EFLG_RX0OVR | EFLG_RX1OVR)) {
            MCP2515_clearRXnOVR();
        } else {
            // Clear generic error interrupt flag
            MCP2515_clearERRIF();
        }
        // Ensure we don't remain stuck thinking an interrupt is pending
        interrupt_pending = false;
        return false;
    }
    
    CAN_FRAME_t frame;  // Array of size 1 containing can_frame structure
    ERROR_t ret = MCP2515_readMessageAfterStatCheck(frame);
    if (ret != ERROR_OK) {
        ESP_LOGE(TAG, "Failed to read message: %d", ret);
        // Clear spurious interrupt flags to avoid IRQ storm
        MCP2515_clearInterrupts();
        interrupt_pending = false;
        return false;
    }
    
    if (frame[0].can_dlc > CAN_MAX_DLEN) {
        ESP_LOGE(TAG, "Received message too long: %d bytes", frame[0].can_dlc);
        return false;
    }
    
    raw_in_msg->id = frame[0].can_id;
    raw_in_msg->dlc = frame[0].can_dlc;
    memcpy(raw_in_msg->data, frame[0].data, frame[0].can_dlc);
    
    // Drain any remaining RX frames to prevent RXnOVR under burst logging or delays
    while (MCP2515_checkReceive()) {
        CAN_FRAME_t drain;
        if (MCP2515_readMessageAfterStatCheck(drain) != ERROR_OK) {
            break;
        }
    }

    interrupt_pending = false;  // Reset interrupt flag after successful read and drain
    return true;
}

