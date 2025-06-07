idf_component_register(
  SRCS "arduino.c"
  INCLUDE_DIRS "."
  PRIV_REQUIRES can_dispatch
)

if(NOT CONFIG_CAN_BACKEND_ARDUINO)
  set_property(TARGET ${COMPONENT_LIB} PROPERTY EXCLUDE_FROM_ALL 1)
endif()
