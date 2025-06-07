idf_component_register(
  SRCS "mcp_multi.c"
  PRIV_REQUIRES can_dispatch
)

if(NOT CONFIG_CAN_BACKEND_MCP_MULTI)
  set_property(TARGET ${COMPONENT_LIB} PROPERTY EXCLUDE_FROM_ALL 1)
endif()
