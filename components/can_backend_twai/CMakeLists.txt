idf_component_register(
    SRCS "twai.c"
    PRIV_REQUIRES can_dispatch
)

# kompiluj jen když je v menuconfigu vybrán TWAI
if(NOT CONFIG_CAN_BACKEND_TWAI)
    set_property(TARGET ${COMPONENT_LIB} PROPERTY EXCLUDE_FROM_ALL 1)
endif()
