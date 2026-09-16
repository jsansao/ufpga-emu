idf_component_register(SRCS "src/emulator.c" "src/pin_map.c" "src/telemetry.c" "src/vcd_writer.c"
                       INCLUDE_DIRS "include"
                       REQUIRES hal)
