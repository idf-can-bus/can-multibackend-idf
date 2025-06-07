idf_component_register(
  SRCS "mcp2515.c"
  PRIV_REQUIRES can_dispatch
)

if(NOT CONFIG_CAN_BACKEND_MCP2515)
  set_property(TARGET ${COMPONENT_LIB} PROPERTY EXCLUDE_FROM_ALL 1)
endif()
