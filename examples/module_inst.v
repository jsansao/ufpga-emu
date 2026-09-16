module dff(input clk, input d, output reg q);
    always @(posedge clk) q <= d;
endmodule

module module_inst(input clk, input d, output q);
    dff u1 (.clk(clk), .d(d), .q(q));
endmodule
