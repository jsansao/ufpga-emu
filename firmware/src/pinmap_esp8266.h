/* Gerado por pc_tool/pinmap_gen.py - NAO EDITAR.
 * Fonte: firmware/pinmaps/esp8266.json */
#ifndef PINMAP_ESP8266_H
#define PINMAP_ESP8266_H

#if defined(EMU_CIRCUIT_COUNTER)
#include "circuit_counter.c"
#define CIRCUIT_NAME "counter"
#elif defined(EMU_CIRCUIT_FSM_101)
#include "circuit_fsm_101.c"
#define CIRCUIT_NAME "fsm_101"
#elif defined(EMU_CIRCUIT_SHIFT_REGISTER)
#include "circuit_shift_register.c"
#define CIRCUIT_NAME "shift_register"
#elif defined(EMU_CIRCUIT_PARAM_COUNTER)
#include "circuit_param_counter.c"
#define CIRCUIT_NAME "param_counter"
#elif defined(EMU_CIRCUIT_PWM)
#include "circuit_pwm.c"
#define CIRCUIT_NAME "pwm"
#elif defined(EMU_CIRCUIT_UART_TX)
#include "circuit_uart_tx.c"
#define CIRCUIT_NAME "uart_tx"
#elif defined(EMU_CIRCUIT_TINY_CPU)
#include "circuit_tiny_cpu.c"
#define CIRCUIT_NAME "tiny_cpu"
#elif defined(EMU_CIRCUIT_TASK_FUNC)
#include "circuit_task_func.c"
#define CIRCUIT_NAME "task_func"
#elif defined(EMU_CIRCUIT_REDUCTION)
#include "circuit_reduction.c"
#define CIRCUIT_NAME "reduction"
#elif defined(EMU_CIRCUIT_PRIORITY_ENCODER)
#include "circuit_priority_encoder.c"
#define CIRCUIT_NAME "priority_encoder"
#elif defined(EMU_CIRCUIT_DECODER)
#include "circuit_decoder.c"
#define CIRCUIT_NAME "decoder"
#elif defined(EMU_CIRCUIT_MIXED)
#include "circuit_mixed.c"
#define CIRCUIT_NAME "mixed"
#elif defined(EMU_CIRCUIT_MUX)
#include "circuit_mux.c"
#define CIRCUIT_NAME "mux"
#elif defined(EMU_CIRCUIT_MUX2)
#include "circuit_mux2.c"
#define CIRCUIT_NAME "mux2"
#elif defined(EMU_CIRCUIT_NEGEDGE_COUNTER)
#include "circuit_negedge_counter.c"
#define CIRCUIT_NAME "negedge_counter"
#elif defined(EMU_CIRCUIT_SIGN_EXTEND)
#include "circuit_sign_extend.c"
#define CIRCUIT_NAME "sign_extend"
#elif defined(EMU_CIRCUIT_CONCAT_MULTI)
#include "circuit_concat_multi.c"
#define CIRCUIT_NAME "concat_multi"
#elif defined(EMU_CIRCUIT_PART_SELECT_LHS)
#include "circuit_part_select_lhs.c"
#define CIRCUIT_NAME "part_select_lhs"
#elif defined(EMU_CIRCUIT_ADDER_N)
#include "circuit_adder_n.c"
#define CIRCUIT_NAME "adder_n"
#elif defined(EMU_CIRCUIT_CASE_EQUALITY)
#include "circuit_case_equality.c"
#define CIRCUIT_NAME "case_equality"
#elif defined(EMU_CIRCUIT_NOT_KEYWORD)
#include "circuit_not_keyword.c"
#define CIRCUIT_NAME "not_keyword"
#elif defined(EMU_CIRCUIT_LOCALPARAM_EXAMPLE)
#include "circuit_localparam_example.c"
#define CIRCUIT_NAME "localparam_example"
#elif defined(EMU_CIRCUIT_MODULE_INST)
#include "circuit_module_inst.c"
#define CIRCUIT_NAME "module_inst"
#elif defined(EMU_CIRCUIT_REPEAT_EXAMPLE)
#include "circuit_repeat_example.c"
#define CIRCUIT_NAME "repeat_example"
#elif defined(EMU_CIRCUIT_ALU)
#include "circuit_alu.c"
#define CIRCUIT_NAME "alu"
#elif defined(EMU_CIRCUIT_BLINKY)
#include "circuit_blinky.c"
#define CIRCUIT_NAME "blinky"
#else
#include "circuit_blinky.c"
#define CIRCUIT_NAME "blinky"
#endif

static const char PINMAP_JSON[] =
    "{"
    "\"counter\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"count[0]\",\"pin\":13,\"bit\":0,\"dir\":\"output\"},{\"name\":\"count[1]\",\"pin\":14,\"bit\":1,\"dir\":\"output\"},{\"name\":\"count[2]\",\"pin\":16,\"bit\":2,\"dir\":\"output\"},{\"name\":\"count[3]\",\"pin\":17,\"bit\":3,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"fsm_101\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"data_in\",\"pin\":13,\"bit\":2,\"dir\":\"input\"},{\"name\":\"detected\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"shift_register\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"load\",\"pin\":13,\"bit\":2,\"dir\":\"input\"},{\"name\":\"data_in\",\"pin\":14,\"bit\":3,\"dir\":\"input\"},{\"name\":\"parallel_load[0]\",\"pin\":15,\"bit\":4,\"dir\":\"input\"},{\"name\":\"parallel_load[1]\",\"pin\":15,\"bit\":5,\"dir\":\"input\"},{\"name\":\"parallel_load[2]\",\"pin\":15,\"bit\":6,\"dir\":\"input\"},{\"name\":\"parallel_load[3]\",\"pin\":15,\"bit\":7,\"dir\":\"input\"},{\"name\":\"parallel_load[4]\",\"pin\":15,\"bit\":8,\"dir\":\"input\"},{\"name\":\"parallel_load[5]\",\"pin\":15,\"bit\":9,\"dir\":\"input\"},{\"name\":\"parallel_load[6]\",\"pin\":15,\"bit\":10,\"dir\":\"input\"},{\"name\":\"parallel_load[7]\",\"pin\":15,\"bit\":11,\"dir\":\"input\"},{\"name\":\"data_out[0]\",\"pin\":2,\"bit\":0,\"dir\":\"output\"},{\"name\":\"data_out[1]\",\"pin\":16,\"bit\":1,\"dir\":\"output\"},{\"name\":\"data_out[2]\",\"pin\":17,\"bit\":2,\"dir\":\"output\"},{\"name\":\"data_out[3]\",\"pin\":18,\"bit\":3,\"dir\":\"output\"},{\"name\":\"data_out[4]\",\"pin\":19,\"bit\":4,\"dir\":\"output\"},{\"name\":\"data_out[5]\",\"pin\":21,\"bit\":5,\"dir\":\"output\"},{\"name\":\"data_out[6]\",\"pin\":22,\"bit\":6,\"dir\":\"output\"},{\"name\":\"data_out[7]\",\"pin\":23,\"bit\":7,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"param_counter\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"count[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},{\"name\":\"count[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},{\"name\":\"count[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},{\"name\":\"count[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"},{\"name\":\"count[4]\",\"pin\":16,\"bit\":4,\"dir\":\"output\"},{\"name\":\"count[5]\",\"pin\":17,\"bit\":5,\"dir\":\"output\"},{\"name\":\"count[6]\",\"pin\":18,\"bit\":6,\"dir\":\"output\"},{\"name\":\"count[7]\",\"pin\":19,\"bit\":7,\"dir\":\"output\"},{\"name\":\"overflow\",\"pin\":2,\"bit\":8,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"pwm\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"enable\",\"pin\":34,\"bit\":2,\"dir\":\"input\"},{\"name\":\"duty[0]\",\"pin\":35,\"bit\":3,\"dir\":\"input\"},{\"name\":\"duty[1]\",\"pin\":36,\"bit\":4,\"dir\":\"input\"},{\"name\":\"duty[2]\",\"pin\":37,\"bit\":5,\"dir\":\"input\"},{\"name\":\"duty[3]\",\"pin\":38,\"bit\":6,\"dir\":\"input\"},{\"name\":\"duty[4]\",\"pin\":39,\"bit\":7,\"dir\":\"input\"},{\"name\":\"duty[5]\",\"pin\":12,\"bit\":8,\"dir\":\"input\"},{\"name\":\"duty[6]\",\"pin\":13,\"bit\":9,\"dir\":\"input\"},{\"name\":\"duty[7]\",\"pin\":14,\"bit\":10,\"dir\":\"input\"},{\"name\":\"period[0]\",\"pin\":15,\"bit\":11,\"dir\":\"input\"},{\"name\":\"period[1]\",\"pin\":16,\"bit\":12,\"dir\":\"input\"},{\"name\":\"period[2]\",\"pin\":17,\"bit\":13,\"dir\":\"input\"},{\"name\":\"period[3]\",\"pin\":18,\"bit\":14,\"dir\":\"input\"},{\"name\":\"period[4]\",\"pin\":19,\"bit\":15,\"dir\":\"input\"},{\"name\":\"period[5]\",\"pin\":21,\"bit\":16,\"dir\":\"input\"},{\"name\":\"period[6]\",\"pin\":22,\"bit\":17,\"dir\":\"input\"},{\"name\":\"period[7]\",\"pin\":23,\"bit\":18,\"dir\":\"input\"},{\"name\":\"pwm_out\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"uart_tx\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"send\",\"pin\":34,\"bit\":2,\"dir\":\"input\"},{\"name\":\"data[0]\",\"pin\":35,\"bit\":3,\"dir\":\"input\"},{\"name\":\"data[1]\",\"pin\":36,\"bit\":4,\"dir\":\"input\"},{\"name\":\"data[2]\",\"pin\":37,\"bit\":5,\"dir\":\"input\"},{\"name\":\"data[3]\",\"pin\":38,\"bit\":6,\"dir\":\"input\"},{\"name\":\"data[4]\",\"pin\":39,\"bit\":7,\"dir\":\"input\"},{\"name\":\"data[5]\",\"pin\":12,\"bit\":8,\"dir\":\"input\"},{\"name\":\"data[6]\",\"pin\":13,\"bit\":9,\"dir\":\"input\"},{\"name\":\"data[7]\",\"pin\":14,\"bit\":10,\"dir\":\"input\"},{\"name\":\"tx\",\"pin\":2,\"bit\":0,\"dir\":\"output\"},{\"name\":\"busy\",\"pin\":15,\"bit\":1,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"tiny_cpu\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"run\",\"pin\":34,\"bit\":2,\"dir\":\"input\"},{\"name\":\"instr[0]\",\"pin\":35,\"bit\":3,\"dir\":\"input\"},{\"name\":\"instr[1]\",\"pin\":36,\"bit\":4,\"dir\":\"input\"},{\"name\":\"instr[2]\",\"pin\":37,\"bit\":5,\"dir\":\"input\"},{\"name\":\"instr[3]\",\"pin\":38,\"bit\":6,\"dir\":\"input\"},{\"name\":\"instr[4]\",\"pin\":39,\"bit\":7,\"dir\":\"input\"},{\"name\":\"instr[5]\",\"pin\":12,\"bit\":8,\"dir\":\"input\"},{\"name\":\"instr[6]\",\"pin\":13,\"bit\":9,\"dir\":\"input\"},{\"name\":\"instr[7]\",\"pin\":14,\"bit\":10,\"dir\":\"input\"},{\"name\":\"instr[8]\",\"pin\":15,\"bit\":11,\"dir\":\"input\"},{\"name\":\"instr[9]\",\"pin\":16,\"bit\":12,\"dir\":\"input\"},{\"name\":\"instr[10]\",\"pin\":17,\"bit\":13,\"dir\":\"input\"},{\"name\":\"instr[11]\",\"pin\":18,\"bit\":14,\"dir\":\"input\"},{\"name\":\"instr[12]\",\"pin\":19,\"bit\":15,\"dir\":\"input\"},{\"name\":\"instr[13]\",\"pin\":21,\"bit\":16,\"dir\":\"input\"},{\"name\":\"instr[14]\",\"pin\":22,\"bit\":17,\"dir\":\"input\"},{\"name\":\"instr[15]\",\"pin\":23,\"bit\":18,\"dir\":\"input\"},{\"name\":\"pc[0]\",\"pin\":25,\"bit\":0,\"dir\":\"output\"},{\"name\":\"pc[1]\",\"pin\":26,\"bit\":1,\"dir\":\"output\"},{\"name\":\"pc[2]\",\"pin\":27,\"bit\":2,\"dir\":\"output\"},{\"name\":\"pc[3]\",\"pin\":32,\"bit\":3,\"dir\":\"output\"},{\"name\":\"pc[4]\",\"pin\":33,\"bit\":4,\"dir\":\"output\"},{\"name\":\"halted\",\"pin\":2,\"bit\":16,\"dir\":\"output\"}],\"virtual_init\":{\"run\":1}},"
    "\"task_func\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"a[0]\",\"pin\":34,\"bit\":2,\"dir\":\"input\"},{\"name\":\"a[1]\",\"pin\":35,\"bit\":3,\"dir\":\"input\"},{\"name\":\"a[2]\",\"pin\":36,\"bit\":4,\"dir\":\"input\"},{\"name\":\"a[3]\",\"pin\":37,\"bit\":5,\"dir\":\"input\"},{\"name\":\"b[0]\",\"pin\":38,\"bit\":6,\"dir\":\"input\"},{\"name\":\"b[1]\",\"pin\":39,\"bit\":7,\"dir\":\"input\"},{\"name\":\"b[2]\",\"pin\":12,\"bit\":8,\"dir\":\"input\"},{\"name\":\"b[3]\",\"pin\":13,\"bit\":9,\"dir\":\"input\"},{\"name\":\"result[0]\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"reduction\":{\"pins\":[{\"name\":\"data[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"data[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"data[2]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"data[3]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"data[4]\",\"pin\":38,\"bit\":4,\"dir\":\"input\"},{\"name\":\"data[5]\",\"pin\":39,\"bit\":5,\"dir\":\"input\"},{\"name\":\"data[6]\",\"pin\":12,\"bit\":6,\"dir\":\"input\"},{\"name\":\"data[7]\",\"pin\":13,\"bit\":7,\"dir\":\"input\"},{\"name\":\"parity\",\"pin\":2,\"bit\":0,\"dir\":\"output\"},{\"name\":\"all_ones\",\"pin\":14,\"bit\":1,\"dir\":\"output\"},{\"name\":\"any_one\",\"pin\":15,\"bit\":2,\"dir\":\"output\"},{\"name\":\"not_zero\",\"pin\":16,\"bit\":3,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"priority_encoder\":{\"pins\":[{\"name\":\"req[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"req[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"req[2]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"req[3]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"code[0]\",\"pin\":14,\"bit\":0,\"dir\":\"output\"},{\"name\":\"code[1]\",\"pin\":15,\"bit\":1,\"dir\":\"output\"},{\"name\":\"valid\",\"pin\":2,\"bit\":2,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"decoder\":{\"pins\":[{\"name\":\"addr[0]\",\"pin\":25,\"bit\":0,\"dir\":\"input\"},{\"name\":\"addr[1]\",\"pin\":26,\"bit\":1,\"dir\":\"input\"},{\"name\":\"y[0]\",\"pin\":13,\"bit\":0,\"dir\":\"output\"},{\"name\":\"y[1]\",\"pin\":14,\"bit\":1,\"dir\":\"output\"},{\"name\":\"y[2]\",\"pin\":16,\"bit\":2,\"dir\":\"output\"},{\"name\":\"y[3]\",\"pin\":17,\"bit\":3,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"mixed\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"a\",\"pin\":34,\"bit\":2,\"dir\":\"input\"},{\"name\":\"b\",\"pin\":35,\"bit\":3,\"dir\":\"input\"},{\"name\":\"count[0]\",\"pin\":14,\"bit\":0,\"dir\":\"output\"},{\"name\":\"count[1]\",\"pin\":15,\"bit\":1,\"dir\":\"output\"},{\"name\":\"y\",\"pin\":2,\"bit\":2,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"mux\":{\"pins\":[{\"name\":\"a\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"b\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"sel\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"y\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"mux2\":{\"pins\":[{\"name\":\"a[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"a[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"b[0]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"b[1]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"sel\",\"pin\":38,\"bit\":4,\"dir\":\"input\"},{\"name\":\"y[0]\",\"pin\":2,\"bit\":0,\"dir\":\"output\"},{\"name\":\"y[1]\",\"pin\":14,\"bit\":1,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"negedge_counter\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"count[0]\",\"pin\":13,\"bit\":0,\"dir\":\"output\"},{\"name\":\"count[1]\",\"pin\":14,\"bit\":1,\"dir\":\"output\"},{\"name\":\"count[2]\",\"pin\":15,\"bit\":2,\"dir\":\"output\"},{\"name\":\"count[3]\",\"pin\":16,\"bit\":3,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"sign_extend\":{\"pins\":[{\"name\":\"value[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"value[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"value[2]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"value[3]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"extended[0]\",\"pin\":12,\"bit\":0,\"dir\":\"output\"},{\"name\":\"extended[1]\",\"pin\":13,\"bit\":1,\"dir\":\"output\"},{\"name\":\"extended[2]\",\"pin\":14,\"bit\":2,\"dir\":\"output\"},{\"name\":\"extended[3]\",\"pin\":15,\"bit\":3,\"dir\":\"output\"},{\"name\":\"extended[4]\",\"pin\":16,\"bit\":4,\"dir\":\"output\"},{\"name\":\"extended[5]\",\"pin\":17,\"bit\":5,\"dir\":\"output\"},{\"name\":\"extended[6]\",\"pin\":18,\"bit\":6,\"dir\":\"output\"},{\"name\":\"extended[7]\",\"pin\":19,\"bit\":7,\"dir\":\"output\"},{\"name\":\"sign_bit\",\"pin\":2,\"bit\":8,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"concat_multi\":{\"pins\":[{\"name\":\"value[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"value[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"value[2]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"value[3]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"out[0]\",\"pin\":14,\"bit\":0,\"dir\":\"output\"},{\"name\":\"out[1]\",\"pin\":15,\"bit\":1,\"dir\":\"output\"},{\"name\":\"out[2]\",\"pin\":16,\"bit\":2,\"dir\":\"output\"},{\"name\":\"out[3]\",\"pin\":17,\"bit\":3,\"dir\":\"output\"},{\"name\":\"out[4]\",\"pin\":18,\"bit\":4,\"dir\":\"output\"},{\"name\":\"out[5]\",\"pin\":19,\"bit\":5,\"dir\":\"output\"},{\"name\":\"out[6]\",\"pin\":21,\"bit\":6,\"dir\":\"output\"},{\"name\":\"out[7]\",\"pin\":22,\"bit\":7,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"part_select_lhs\":{\"pins\":[{\"name\":\"clk\",\"pin\":12,\"bit\":0,\"dir\":\"input\"},{\"name\":\"value[0]\",\"pin\":34,\"bit\":1,\"dir\":\"input\"},{\"name\":\"value[1]\",\"pin\":35,\"bit\":2,\"dir\":\"input\"},{\"name\":\"value[2]\",\"pin\":36,\"bit\":3,\"dir\":\"input\"},{\"name\":\"value[3]\",\"pin\":37,\"bit\":4,\"dir\":\"input\"},{\"name\":\"load\",\"pin\":38,\"bit\":5,\"dir\":\"input\"},{\"name\":\"out[0]\",\"pin\":14,\"bit\":0,\"dir\":\"output\"},{\"name\":\"out[1]\",\"pin\":15,\"bit\":1,\"dir\":\"output\"},{\"name\":\"out[2]\",\"pin\":16,\"bit\":2,\"dir\":\"output\"},{\"name\":\"out[3]\",\"pin\":17,\"bit\":3,\"dir\":\"output\"},{\"name\":\"out[4]\",\"pin\":18,\"bit\":4,\"dir\":\"output\"},{\"name\":\"out[5]\",\"pin\":19,\"bit\":5,\"dir\":\"output\"},{\"name\":\"out[6]\",\"pin\":21,\"bit\":6,\"dir\":\"output\"},{\"name\":\"out[7]\",\"pin\":22,\"bit\":7,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"adder_n\":{\"pins\":[{\"name\":\"a[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"a[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"a[2]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"a[3]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"b[0]\",\"pin\":38,\"bit\":4,\"dir\":\"input\"},{\"name\":\"b[1]\",\"pin\":39,\"bit\":5,\"dir\":\"input\"},{\"name\":\"b[2]\",\"pin\":12,\"bit\":6,\"dir\":\"input\"},{\"name\":\"b[3]\",\"pin\":13,\"bit\":7,\"dir\":\"input\"},{\"name\":\"sum[0]\",\"pin\":14,\"bit\":0,\"dir\":\"output\"},{\"name\":\"sum[1]\",\"pin\":15,\"bit\":1,\"dir\":\"output\"},{\"name\":\"sum[2]\",\"pin\":16,\"bit\":2,\"dir\":\"output\"},{\"name\":\"sum[3]\",\"pin\":17,\"bit\":3,\"dir\":\"output\"},{\"name\":\"carry\",\"pin\":2,\"bit\":4,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"case_equality\":{\"pins\":[{\"name\":\"a[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"a[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"a[2]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"a[3]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"b[0]\",\"pin\":38,\"bit\":4,\"dir\":\"input\"},{\"name\":\"b[1]\",\"pin\":39,\"bit\":5,\"dir\":\"input\"},{\"name\":\"b[2]\",\"pin\":12,\"bit\":6,\"dir\":\"input\"},{\"name\":\"b[3]\",\"pin\":13,\"bit\":7,\"dir\":\"input\"},{\"name\":\"eq\",\"pin\":2,\"bit\":0,\"dir\":\"output\"},{\"name\":\"neq\",\"pin\":14,\"bit\":1,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"not_keyword\":{\"pins\":[{\"name\":\"a\",\"pin\":26,\"bit\":0,\"dir\":\"input\"},{\"name\":\"b\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"y\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"localparam_example\":{\"pins\":[{\"name\":\"in[0]\",\"pin\":34,\"bit\":0,\"dir\":\"input\"},{\"name\":\"in[1]\",\"pin\":35,\"bit\":1,\"dir\":\"input\"},{\"name\":\"in[2]\",\"pin\":36,\"bit\":2,\"dir\":\"input\"},{\"name\":\"in[3]\",\"pin\":37,\"bit\":3,\"dir\":\"input\"},{\"name\":\"out[0]\",\"pin\":2,\"bit\":0,\"dir\":\"output\"},{\"name\":\"out[1]\",\"pin\":14,\"bit\":1,\"dir\":\"output\"},{\"name\":\"out[2]\",\"pin\":15,\"bit\":2,\"dir\":\"output\"},{\"name\":\"out[3]\",\"pin\":16,\"bit\":3,\"dir\":\"output\"},{\"name\":\"out[4]\",\"pin\":17,\"bit\":4,\"dir\":\"output\"},{\"name\":\"out[5]\",\"pin\":18,\"bit\":5,\"dir\":\"output\"},{\"name\":\"out[6]\",\"pin\":19,\"bit\":6,\"dir\":\"output\"},{\"name\":\"out[7]\",\"pin\":21,\"bit\":7,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"module_inst\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"d\",\"pin\":34,\"bit\":1,\"dir\":\"input\"},{\"name\":\"q\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"repeat_example\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"value[0]\",\"pin\":34,\"bit\":2,\"dir\":\"input\"},{\"name\":\"value[1]\",\"pin\":35,\"bit\":3,\"dir\":\"input\"},{\"name\":\"value[2]\",\"pin\":36,\"bit\":4,\"dir\":\"input\"},{\"name\":\"value[3]\",\"pin\":37,\"bit\":5,\"dir\":\"input\"},{\"name\":\"value[4]\",\"pin\":38,\"bit\":6,\"dir\":\"input\"},{\"name\":\"value[5]\",\"pin\":39,\"bit\":7,\"dir\":\"input\"},{\"name\":\"value[6]\",\"pin\":12,\"bit\":8,\"dir\":\"input\"},{\"name\":\"value[7]\",\"pin\":13,\"bit\":9,\"dir\":\"input\"},{\"name\":\"n[0]\",\"pin\":14,\"bit\":10,\"dir\":\"input\"},{\"name\":\"n[1]\",\"pin\":15,\"bit\":11,\"dir\":\"input\"},{\"name\":\"n[2]\",\"pin\":16,\"bit\":12,\"dir\":\"input\"},{\"name\":\"result[0]\",\"pin\":2,\"bit\":0,\"dir\":\"output\"},{\"name\":\"result[1]\",\"pin\":17,\"bit\":1,\"dir\":\"output\"},{\"name\":\"result[2]\",\"pin\":18,\"bit\":2,\"dir\":\"output\"},{\"name\":\"result[3]\",\"pin\":19,\"bit\":3,\"dir\":\"output\"},{\"name\":\"result[4]\",\"pin\":21,\"bit\":4,\"dir\":\"output\"},{\"name\":\"result[5]\",\"pin\":22,\"bit\":5,\"dir\":\"output\"},{\"name\":\"result[6]\",\"pin\":23,\"bit\":6,\"dir\":\"output\"},{\"name\":\"result[7]\",\"pin\":25,\"bit\":7,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"alu\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"a[0]\",\"pin\":34,\"bit\":2,\"dir\":\"input\"},{\"name\":\"a[1]\",\"pin\":35,\"bit\":3,\"dir\":\"input\"},{\"name\":\"a[2]\",\"pin\":36,\"bit\":4,\"dir\":\"input\"},{\"name\":\"a[3]\",\"pin\":37,\"bit\":5,\"dir\":\"input\"},{\"name\":\"b[0]\",\"pin\":38,\"bit\":6,\"dir\":\"input\"},{\"name\":\"b[1]\",\"pin\":39,\"bit\":7,\"dir\":\"input\"},{\"name\":\"b[2]\",\"pin\":12,\"bit\":8,\"dir\":\"input\"},{\"name\":\"b[3]\",\"pin\":13,\"bit\":9,\"dir\":\"input\"},{\"name\":\"op[0]\",\"pin\":26,\"bit\":10,\"dir\":\"input\"},{\"name\":\"op[1]\",\"pin\":27,\"bit\":11,\"dir\":\"input\"},{\"name\":\"op[2]\",\"pin\":28,\"bit\":12,\"dir\":\"input\"},{\"name\":\"result[0]\",\"pin\":14,\"bit\":0,\"dir\":\"output\"},{\"name\":\"result[1]\",\"pin\":15,\"bit\":1,\"dir\":\"output\"},{\"name\":\"result[2]\",\"pin\":16,\"bit\":2,\"dir\":\"output\"},{\"name\":\"result[3]\",\"pin\":17,\"bit\":3,\"dir\":\"output\"},{\"name\":\"result[4]\",\"pin\":18,\"bit\":4,\"dir\":\"output\"},{\"name\":\"result[5]\",\"pin\":19,\"bit\":5,\"dir\":\"output\"},{\"name\":\"result[6]\",\"pin\":21,\"bit\":6,\"dir\":\"output\"},{\"name\":\"result[7]\",\"pin\":22,\"bit\":7,\"dir\":\"output\"},{\"name\":\"valid\",\"pin\":2,\"bit\":8,\"dir\":\"output\"}],\"virtual_init\":{}},"
    "\"blinky\":{\"pins\":[{\"name\":\"clk\",\"pin\":4,\"bit\":0,\"dir\":\"input\"},{\"name\":\"rst\",\"pin\":5,\"bit\":1,\"dir\":\"input\"},{\"name\":\"led\",\"pin\":2,\"bit\":0,\"dir\":\"output\"}],\"virtual_init\":{}}"
    "}";

#endif /* PINMAP_ESP8266_H */
