module concat_multi (
    input  wire [3:0] value,
    output reg  [7:0] out
);
    always @(*) begin
        out = {4'b1111, value};
    end
endmodule
