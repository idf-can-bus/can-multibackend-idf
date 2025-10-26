#pragma once

#include "can_dispatch.h"

void init_hardware(can_config_t *hw_config_ptr);

// Instance counts are part of can_config_t for MULTI backend (bundle with instance_count).
