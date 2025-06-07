#include "can_backend_twai.h"
#include <stdio.h>
#include "esp_log.h"
#include "driver/twai.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <inttypes.h>  // for PRIu32, PRIu8, ect.

static const char* TAG = "can_backend_twai";

// Remember TWAI configuration from can_twai_init
static twai_config_t twai_config;

// Initialize CAN hardware
bool can_twai_init(const twai_config_t *cfg) 
{
    ESP_LOGD(TAG, "Initializing TWAI driver with:");
    ESP_LOGD(TAG, "  TX GPIO: %d", (int)cfg->general_config.tx_io);
    ESP_LOGD(TAG, "  RX GPIO: %d", (int)cfg->general_config.rx_io);
    ESP_LOGD(TAG, "  Mode: %s", cfg->general_config.mode == TWAI_MODE_NORMAL ? "Normal" :
                                 cfg->general_config.mode == TWAI_MODE_NO_ACK ? "No Ack" : "Listen Only");

    // Install TWAI driver with provided configuration
    esp_err_t err = twai_driver_install(&cfg->general_config, 
                                      &cfg->timing_config, 
                                      &cfg->filter_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install TWAI driver: %s", esp_err_to_name(err));
        return false;
    }

    // Start TWAI driver
    err = twai_start();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start TWAI: %s", esp_err_to_name(err));
        twai_driver_uninstall();
        return false;
    }
   
    twai_config = *cfg;

    ESP_LOGI(TAG, "TWAI started successfully (rx_timeout=%ldms, tx_timeout=%ldms)", 
             pdTICKS_TO_MS(twai_config.receive_timeout), 
             pdTICKS_TO_MS(twai_config.transmit_timeout));

    
    return true;
}

// Deinitialize CAN hardware
bool can_twai_deinit() 
{
     // Stop TWAI driver
    esp_err_t err = twai_stop();
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Failed to stop TWAI: %s", esp_err_to_name(err));
        return false;
    }

    // Uninstall TWAI driver
    err = twai_driver_uninstall();
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Failed to uninstall TWAI driver: %s", esp_err_to_name(err));
        return false;
    }

    return true;
}


bool can_twai_send(const can_message_t *raw_out_msg)
{
    // Validate message length
    if (raw_out_msg->dlc > TWAI_FRAME_MAX_DLC) {
        ESP_LOGE(TAG, "Invalid message length: %d", raw_out_msg->dlc);
        return false;
    }

    // Prepare TWAI message
    twai_message_t msg = {
        .flags = 0,
        .identifier = raw_out_msg->id,
        .data_length_code = raw_out_msg->dlc,
        .data = {0}
    };
       
    // Copy raw_out_msg->data to message
    memcpy(msg.data, raw_out_msg->data, raw_out_msg->dlc);

    // Transmit message with configured timeout
    esp_err_t err = twai_transmit(&msg, twai_config.transmit_timeout);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to send message: %s", esp_err_to_name(err));
        can_twai_reset_twai_if_needed();
        return false;
    }
    ESP_LOGD(TAG, "Message sent: ID=0x%lX", raw_out_msg->id);
    return true;
}

/**
 * Checks TWAI controller status and resets it if necessary.
 * This handles bus-off conditions and restarts the controller
 * if it's not in the running state.
 */
void can_twai_reset_twai_if_needed(void) {
    twai_status_info_t status;
    if (twai_get_status_info(&status) == ESP_OK) {
        if (status.state == TWAI_STATE_BUS_OFF) {
            ESP_LOGW(TAG, "Bus-off detected, initiating recovery...");
            twai_initiate_recovery();
            vTaskDelay(twai_config.bus_off_timeout);  // wait for recovery
        } else if (status.state != TWAI_STATE_RUNNING) {
            ESP_LOGW(TAG, "Controller not running (state=%d), restarting...", (int)status.state);
            twai_stop();
            vTaskDelay(twai_config.bus_not_running_timeout);
            twai_start();
        }
    }
} // can_twai_reset_twai_if_needed

bool can_twai_receive(can_message_t *raw_in_msg)
{
    // Validate input buffer
    if (raw_in_msg == NULL) {
        ESP_LOGE(TAG, "Invalid input buffer");
        return false;
    }

    // Receive message with configured timeout
    twai_message_t msg;
    esp_err_t err = twai_receive(&msg, twai_config.receive_timeout);
    
    if (err == ESP_OK) {
        // Process received message
        raw_in_msg->id = msg.identifier;
        raw_in_msg->dlc = msg.data_length_code;
        if (msg.data_length_code <= TWAI_FRAME_MAX_DLC) {
            memcpy(raw_in_msg->data, msg.data, msg.data_length_code);
            ESP_LOGD(TAG, "Received ID=0x%lX LEN=%d", msg.identifier, msg.data_length_code);
        } else {
            ESP_LOGW(TAG, "Received message with invalid DLC: %d", msg.data_length_code);
            return false;
        }
        return true;
    } else if (err != ESP_ERR_TIMEOUT) {
        // Log only real errors, timeout is expected
       ESP_LOGE(TAG, "Error receiving message: %s (error code: %d)", 
                 esp_err_to_name(err), err);
        can_twai_reset_twai_if_needed();
        return false;
    }    
    return false;
}

