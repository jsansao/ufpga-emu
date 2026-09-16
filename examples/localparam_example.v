module localparam_example #(parameter WIDTH = 4)(
    input  [WIDTH-1:0] in,
    output [7:0]       out
);
    localparam SHIFT = 2;
    assign out = in << SHIFT;
endmodule
