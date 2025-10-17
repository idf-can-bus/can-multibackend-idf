set(EXAMPLES_DIR ${CMAKE_SOURCE_DIR}/examples)

# Vždy registrovat 'main' – bez app_main
set(APP_SRC "${EXAMPLES_DIR}/init_hardware.c")

# Podle Kconfig přidat vybraný příklad (ten definuje app_main)
if(CONFIG_EXAMPLE_SEND_SINGLE)
    list(APPEND APP_SRC "${EXAMPLES_DIR}/single/send_single.c")
elseif(CONFIG_EXAMPLE_RECV_POLL_SINGLE)
    list(APPEND APP_SRC "${EXAMPLES_DIR}/single/receive_poll_single.c")
elseif(CONFIG_EXAMPLE_RECV_INT_SINGLE)
    list(APPEND APP_SRC "${EXAMPLES_DIR}/single/receive_interrupt_single.c")
elseif(CONFIG_EXAMPLE_SEND_MULTI)
    list(APPEND APP_SRC "${EXAMPLES_DIR}/multi/send_multi.c")
elseif(CONFIG_EXAMPLE_RECV_POLL_MULTI)
    list(APPEND APP_SRC "${EXAMPLES_DIR}/multi/receive_poll_multi.c")
elseif(CONFIG_EXAMPLE_RECV_INT_MULTI)
    list(APPEND APP_SRC "${EXAMPLES_DIR}/multi/receive_interrupt_multi.c")
endif()

idf_component_register(
    SRCS ${APP_SRC}
    INCLUDE_DIRS "." "${EXAMPLES_DIR}"
    REQUIRES can_dispatch examples_utils
)
