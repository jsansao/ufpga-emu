idf_component_register(SRCS "main_esp32.c"
                        "../lib/hal/src/hal_gpio.c"
                        "../lib/hal/src/hal_serial.c"
                        "../lib/hal/src/hal_timer.c"
                        "../lib/hal/src/hal_mutex.c"
                        "../lib/runtime/src/emulator.c"
                        "../lib/runtime/src/pin_map.c"
                        "../lib/runtime/src/telemetry.c")
