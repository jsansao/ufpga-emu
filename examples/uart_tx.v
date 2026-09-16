module uart_tx #(
    parameter CLK_DIV = 8
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       send,
    input  wire [7:0] data,
    output reg        tx,
    output reg        busy
);

    reg [3:0] clk_cnt;
    reg [3:0] bit_idx;
    reg [7:0] shift;
    reg       active;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            clk_cnt <= 0;
            bit_idx <= 0;
            shift   <= 0;
            active  <= 0;
            tx      <= 1;
            busy    <= 0;
        end else begin
            if (!active) begin
                if (send) begin
                    active  <= 1;
                    shift   <= data;
                    bit_idx <= 0;
                    clk_cnt <= 0;
                    tx      <= 0;
                    busy    <= 1;
                end
            end else begin
                if (clk_cnt == CLK_DIV - 1) begin
                    clk_cnt <= 0;
                    if (bit_idx == 9) begin
                        active <= 0;
                        busy   <= 0;
                        tx     <= 1;
                    end else begin
                        bit_idx <= bit_idx + 1;
                        if (bit_idx < 8)
                            tx <= shift[0];
                        else
                            tx <= 1;
                        shift <= {shift[6:0], 1'b0};
                    end
                end else begin
                    clk_cnt <= clk_cnt + 1;
                end
            end
        end
    end

endmodule
