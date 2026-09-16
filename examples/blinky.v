// Exemplo: Blinky com contador de 50k ciclos
// Entradas: clk, rst
// Saida: led (alterna a cada 50000 ciclos)

module blinky (
    input  wire clk,
    input  wire rst,
    output reg  led
);

    reg [15:0] counter;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            counter <= 16'b0;
            led     <= 1'b0;
        end else begin
            if (counter == 16'd50000) begin
                counter <= 16'b0;
                led     <= ~led;
            end else begin
                counter <= counter + 1'b1;
            end
        end
    end

endmodule
