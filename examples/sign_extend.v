module sign_extend (
    input  wire [3:0] value,
    output reg  [7:0] extended,
    output reg        sign_bit
);
    always @(*) begin
        if (value[3])
            extended = value | 8'hF0;
        else
            extended = value;
        sign_bit = value[3];
    end
endmodule
