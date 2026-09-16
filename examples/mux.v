module mux(
    input  wire a,
    input  wire b,
    input  wire sel,
    output reg  y
);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = b;
    end
endmodule
