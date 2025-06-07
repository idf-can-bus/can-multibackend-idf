set(EXAMPLES_DIR ${CMAKE_SOURCE_DIR}/examples)

set(APP_SRC "")

if(CONFIG_EXAMPLE_SEND_SINGLE)
    set(APP_SRC "${EXAMPLES_DIR}/send_single.c")
elseif(CONFIG_EXAMPLE_RECV_POLL_SINGLE)
    set(APP_SRC "${EXAMPLES_DIR}/receive_poll_single.c")
elseif(CONFIG_EXAMPLE_RECV_INT_SINGLE)
    set(APP_SRC "${EXAMPLES_DIR}/receive_interrupt_single.c")
elseif(CONFIG_EXAMPLE_SEND_MULTI)
    set(APP_SRC "${EXAMPLES_DIR}/send_multi.c")
elseif(CONFIG_EXAMPLE_RECV_POLL_MULTI)
    set(APP_SRC "${EXAMPLES_DIR}/receive_poll_multi.c")
elseif(CONFIG_EXAMPLE_RECV_INT_MULTI)
    set(APP_SRC "${EXAMPLES_DIR}/receive_interrupt_multi.c")
endif()

# Stop build if no example is selected
#if(APP_SRC STREQUAL "")
#    message(FATAL_ERROR "No example selected in menuconfig!")
#endif()

idf_component_register(
    SRCS "${APP_SRC}"
    INCLUDE_DIRS "."
    REQUIRES can_dispatch
)
