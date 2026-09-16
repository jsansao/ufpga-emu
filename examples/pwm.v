module pwm #(
    parameter WIDTH = 8
)(
    input  wire             clk,
    input  wire             rst,
    input  wire             enable,
    input  wire [WIDTH-1:0] duty,
    input  wire [WIDTH-1:0] period,
    output reg              pwm_out
);

    reg [WIDTH-1:0] counter;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            counter  <= 0;
            pwm_out  <= 0;
        end else if (!enable) begin
            counter  <= 0;
            pwm_out  <= 0;
        end else if (counter >= period) begin
            counter  <= 0;
            pwm_out  <= (duty != 0);
        end else if (counter < duty) begin
            counter  <= counter + 1;
            pwm_out  <= 1;
        end else begin
            counter  <= counter + 1;
            pwm_out  <= 0;
        end
    end

endmodule
