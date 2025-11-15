# Select example source based on Kconfig
# Examples are compiled from their component directories using can_dispatch for backend abstraction

if(CONFIG_EXAMPLE_SEND_SINGLE)
    # Use TWAI example with can_dispatch providing backend abstraction
    set(APP_SRC "${CMAKE_SOURCE_DIR}/components/twai-idf-can/examples/send/main/main.c")
    set(EXTRA_INCLUDE_DIRS 
        "${CMAKE_SOURCE_DIR}/components/twai-idf-can/examples"
        "${CMAKE_SOURCE_DIR}/components/twai-idf-can/include"
    )
elseif(CONFIG_EXAMPLE_RECV_POLL_SINGLE)
    set(APP_SRC "${CMAKE_SOURCE_DIR}/components/twai-idf-can/examples/receive_poll/main/main.c")
    set(EXTRA_INCLUDE_DIRS 
        "${CMAKE_SOURCE_DIR}/components/twai-idf-can/examples"
        "${CMAKE_SOURCE_DIR}/components/twai-idf-can/include"
    )
elseif(CONFIG_EXAMPLE_RECV_INT_SINGLE)
    set(APP_SRC "${CMAKE_SOURCE_DIR}/components/twai-idf-can/examples/receive_interrupt/main/main.c")
    set(EXTRA_INCLUDE_DIRS 
        "${CMAKE_SOURCE_DIR}/components/twai-idf-can/examples"
        "${CMAKE_SOURCE_DIR}/components/twai-idf-can/include"
    )
elseif(CONFIG_EXAMPLE_SEND_MULTI)
    set(APP_SRC "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/examples/send/main/main.c")
    set(EXTRA_INCLUDE_DIRS 
        "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/examples"
        "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/include"
    )
elseif(CONFIG_EXAMPLE_RECV_POLL_MULTI)
    set(APP_SRC "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/examples/receive_poll/main/main.c")
    set(EXTRA_INCLUDE_DIRS 
        "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/examples"
        "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/include"
    )
elseif(CONFIG_EXAMPLE_RECV_INT_MULTI)
    set(APP_SRC "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/examples/receive_interrupt/main/main.c")
    set(EXTRA_INCLUDE_DIRS 
        "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/examples"
        "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/include"
    )
endif()

# Build required component list conditionally by selected backend
# Note: examples-utils-idf-can is provided by example submodules via EXTRA_COMPONENT_DIRS
set(REQUIRES_DEPS can_dispatch examples-utils-idf-can)

if(CONFIG_CAN_BACKEND_TWAI)
    list(APPEND REQUIRES_DEPS twai-idf-can)
endif()

if(CONFIG_CAN_BACKEND_MCP2515_SINGLE)
    list(APPEND REQUIRES_DEPS mcp2515-esp32-idf)
    # unified MCP2515 config types are provided by the multi component
    list(APPEND REQUIRES_DEPS mcp25xxx-multi-idf-can)
endif()

if(CONFIG_CAN_BACKEND_MCP2515_MULTI)
    list(APPEND REQUIRES_DEPS mcp25xxx-multi-idf-can)
endif()

idf_component_register(
    SRCS ${APP_SRC}
    INCLUDE_DIRS "." ${EXTRA_INCLUDE_DIRS}
    REQUIRES ${REQUIRES_DEPS}
)
