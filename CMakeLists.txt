# The following five lines of boilerplate have to be in your project's
# CMakeLists in this exact order for cmake to work correctly
cmake_minimum_required(VERSION 3.16)

# Add paths to nested components (examples-utils-idf-can inside submodules)
set(EXTRA_COMPONENT_DIRS 
    "${CMAKE_SOURCE_DIR}/components/twai-idf-can/components"
    "${CMAKE_SOURCE_DIR}/components/mcp25xxx-multi-idf-can/components"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(esp32-can-idf)

