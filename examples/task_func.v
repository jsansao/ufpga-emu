/*
 * Exemplo: task e function
 * Task: multiplicacao com output
 * Function: soma combinacional
 */
module task_func(
    input clk,
    input rst,
    input [3:0] a,
    input [3:0] b,
    output reg [7:0] result
);
    task mult_task;
        input [3:0] x;
        input [3:0] y;
        output [7:0] z;
        reg [3:0] i;
        begin
            z = 0;
            for (i = 0; i < 4; i = i + 1) begin
                if (y[i])
                    z = z + (x << i);
            end
        end
    endtask

    function [7:0] add_func;
        input [3:0] x;
        input [3:0] y;
        begin
            add_func = x + y;
        end
    endfunction

    always @(posedge clk or posedge rst) begin
        if (rst)
            result <= 0;
        else begin
            mult_task(a, b, result);
            if (result == 0)
                result <= add_func(a, b);
        end
    end
endmodule
