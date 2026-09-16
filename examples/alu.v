module alu(
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire [1:0] op,
    output reg  [3:0] y,
    output reg        lt,
    output reg        gt,
    output reg        le,
    output reg        ge
);

    always @(*) begin
        case (op)
            2'b00:   y = a + b;
            2'b01:   y = a * b;
            2'b10:   y = a / b;
            2'b11:   y = a % b;
            default: y = 4'b0;
        endcase
        lt = (a < b);
        gt = (a > b);
        le = (a <= b);
        ge = (a >= b);
    end

endmodule
