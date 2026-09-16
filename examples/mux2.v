module mux2(
    input  wire [1:0] a,
    input  wire [1:0] b,
    input  wire       sel,
    output reg  [1:0] y
);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = b;
    end
endmodule
