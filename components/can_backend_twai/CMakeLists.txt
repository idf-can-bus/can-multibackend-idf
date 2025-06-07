idf_component_register(
    SRCS "can_backend_twai.c"
    INCLUDE_DIRS "."
    REQUIRES can_iface driver
)

# compile only if TWAI is selected in menuconfig
# if(NOT CONFIG_CAN_BACKEND_TWAI)
#     set_property(TARGET ${COMPONENT_LIB} PROPERTY EXCLUDE_FROM_ALL 1)
# endif()
