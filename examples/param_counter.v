module param_counter #(
    parameter WIDTH = 8,
    parameter MAX_VAL = 255
) (
    input  wire             clk,
    input  wire             rst,
    output reg [WIDTH-1:0]  count,
    output reg              overflow
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count    <= 0;
            overflow <= 0;
        end else begin
            if (count == MAX_VAL) begin
                count    <= 0;
                overflow <= 1;
            end else begin
                count    <= count + 1;
                overflow <= 0;
            end
        end
    end

endmodule
