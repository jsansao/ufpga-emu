module negedge_counter (
    input  wire       clk,
    input  wire       rst,
    output reg  [3:0] count
);
    always @(negedge clk or posedge rst) begin
        if (rst)
            count <= 4'b0;
        else
            count <= count + 4'b1;
    end
endmodule
