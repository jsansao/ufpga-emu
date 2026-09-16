module mixed(
    input  wire       clk,
    input  wire       rst,
    input  wire       a,
    input  wire       b,
    output reg  [1:0] count,
    output reg        y
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 2'b0;
        else
            count <= count + 1'b1;
    end

    always @(*) begin
        if (a & b)
            y = 1'b1;
        else
            y = 1'b0;
    end
endmodule
