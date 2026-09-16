// Detector de sequencia "101" (Maquina de Moore)
// Entradas: clk, rst, data_in
// Saida: detected

module fsm_101 (
    input  wire clk,
    input  wire rst,
    input  wire data_in,
    output reg  detected
);

    reg [1:0] state;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state    <= 2'b00;
            detected <= 1'b0;
        end else begin
            case (state)
                2'b00: begin
                    if (data_in)
                        state <= 2'b01;
                    else
                        state <= 2'b00;
                    detected <= 1'b0;
                end
                2'b01: begin
                    if (data_in)
                        state <= 2'b01;
                    else
                        state <= 2'b10;
                    detected <= 1'b0;
                end
                2'b10: begin
                    if (data_in) begin
                        state    <= 2'b01;
                        detected <= 1'b1;
                    end else begin
                        state    <= 2'b00;
                        detected <= 1'b0;
                    end
                end
                default: begin
                    state    <= 2'b00;
                    detected <= 1'b0;
                end
            endcase
        end
    end

endmodule
