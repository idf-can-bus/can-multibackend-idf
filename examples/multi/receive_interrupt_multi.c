#include "can_dispatch.h"
#include <stdio.h>

void app_main(void)
{
    can_iface_config_t cfg = { .bitrate = 500000 };
    can_iface_init(&cfg);
    uint8_t data[8] = {0};
    while (1) {
        can_iface_transmit(data, 8);
        printf("frame sent\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
