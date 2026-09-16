module part_select_lhs (
    input  wire       clk,
    input  wire [3:0] value,
    input  wire       load,
    output reg  [7:0] out
);
    always @(posedge clk) begin
        if (load)
            out[7:4] <= value;
        else
            out[7:4] <= 4'h0;
    end
endmodule
