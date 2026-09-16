module adder_n #(
    parameter N = 4
) (
    input  wire [N-1:0] a,
    input  wire [N-1:0] b,
    output reg  [N-1:0] sum,
    output reg          carry
);
    reg [N:0] wide;
    always @(*) begin
        wide = a + b;
        sum = wide[N-1:0];
        carry = wide[N];
    end
endmodule
