module priority_encoder (
    input  wire [3:0] req,
    output reg  [1:0] code,
    output reg        valid
);
    integer i;
    always @(*) begin
        code  = 2'b0;
        valid = 1'b0;
        for (i = 3; i >= 0; i = i - 1) begin
            if (req[i]) begin
                code  = i;
                valid = 1'b1;
            end
        end
    end
endmodule
