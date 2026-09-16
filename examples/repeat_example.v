module repeat_example(
    input clk,
    input rst,
    input [7:0] value,
    input [2:0] n,
    output reg [7:0] result
);
    reg [7:0] tmp;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            result <= 8'd0;
        end else begin
            tmp = value;
            repeat (n)
                tmp = tmp << 1;
            result <= tmp;
        end
    end
endmodule
