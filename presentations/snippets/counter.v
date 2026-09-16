// counter.v - contador de 4 bits
module counter (
    input  wire       clk,
    input  wire       rst,
    output reg  [3:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 4'b0;
        else
            count <= count + 4'b1;
    end
endmodule
