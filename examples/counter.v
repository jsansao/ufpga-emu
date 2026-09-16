// Exemplo: Contador de 4 bits
// Entradas: clk, rst
// Saida: count (4 bits mapeados em 4 GPIOs)

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
