#include "can_dispatch.h"
#include <stdio.h>
#include "examples_utils.h"

void app_main(void)
{
    can_iface_config_t cfg = { .bitrate = 500000 };
    can_iface_init(&cfg);
    uint8_t data[8] = {0};
    while (1) {
        can_iface_transmit(data, 8);
        printf("frame sent\n");
        sleep_ms_min_ticks(1000);
    }
}
