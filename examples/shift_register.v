// Shift register de 8 bits com load paralelo
// Entradas: clk, rst, load, data_in (serial), parallel_load (8 bits)
// Saidas: data_out (8 bits)

module shift_register (
    input  wire       clk,
    input  wire       rst,
    input  wire       load,
    input  wire       data_in,
    input  wire [7:0] parallel_load,
    output reg  [7:0] data_out
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            data_out <= 8'b0;
        end else if (load) begin
            data_out <= parallel_load;
        end else begin
            data_out <= {data_out[6:0], data_in};
        end
    end

endmodule
