module reduction (
    input  wire [7:0] data,
    output reg        parity,
    output reg        all_ones,
    output reg        any_one,
    output reg        not_zero
);
    always @(*) begin
        parity    = ^data;
        all_ones  = &data;
        any_one   = |data;
        not_zero  = (^data) ? 1'b1 : 1'b0;
    end
endmodule
