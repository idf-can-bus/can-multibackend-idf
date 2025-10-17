set(MULTI_SRC
  mcp2515_multi_adapter.c
  mcp2515-esp32_multi/mcp2515_multi.c
)

idf_component_register(
  SRCS ${MULTI_SRC}
  INCLUDE_DIRS "." "mcp2515-esp32_multi"
  PRIV_REQUIRES can_iface driver freertos esp_timer
)

if(NOT CONFIG_CAN_BACKEND_MCP2515_MULTI)
  set_property(TARGET ${COMPONENT_LIB} PROPERTY EXCLUDE_FROM_ALL 1)
endif()
