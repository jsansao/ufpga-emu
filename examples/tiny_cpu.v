module tiny_cpu(
    input  wire        clk,
    input  wire        rst,
    input  wire        run,
    input  wire [15:0] instr,
    output reg  [7:0]  pc,
    output reg  [7:0]  dout,
    output reg         halted
);

    reg [7:0]  r0, r1, r2, r3;
    reg [7:0]  imm;
    reg [3:0]  opcode;
    reg [1:0]  rd, rs;
    reg        phase;
    reg [7:0]  src_val;
    reg [7:0]  dst_val;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            pc      <= 0;
            r0      <= 0;
            r1      <= 0;
            r2      <= 0;
            r3      <= 0;
            imm     <= 0;
            opcode  <= 0;
            rd      <= 0;
            rs      <= 0;
            phase   <= 0;
            src_val <= 0;
            dst_val <= 0;
            dout    <= 0;
            halted  <= 0;
        end else if (run) begin
            if (!phase) begin
                opcode <= instr[15:12];
                rd     <= instr[11:10];
                rs     <= instr[9:8];
                imm    <= instr[7:0];
                pc     <= pc + 1;
                phase  <= 1;
            end else begin
                case (opcode)
                    4'h0: begin
                        phase <= 0;
                    end
                    4'h1: begin
                        case (rd)
                            0: r0 <= imm;
                            1: r1 <= imm;
                            2: r2 <= imm;
                            3: r3 <= imm;
                        endcase
                        dout  <= imm;
                        phase <= 0;
                    end
                    4'h2: begin
                        case (rs)
                            0: src_val = r0;
                            1: src_val = r1;
                            2: src_val = r2;
                            3: src_val = r3;
                        endcase
                        case (rd)
                            0: r0 <= src_val;
                            1: r1 <= src_val;
                            2: r2 <= src_val;
                            3: r3 <= src_val;
                        endcase
                        dout  <= src_val;
                        phase <= 0;
                    end
                    4'h3: begin
                        case (rs)
                            0: src_val = r0;
                            1: src_val = r1;
                            2: src_val = r2;
                            3: src_val = r3;
                        endcase
                        case (rd)
                            0: dst_val = r0;
                            1: dst_val = r1;
                            2: dst_val = r2;
                            3: dst_val = r3;
                        endcase
                        case (rd)
                            0: r0 <= dst_val + src_val;
                            1: r1 <= dst_val + src_val;
                            2: r2 <= dst_val + src_val;
                            3: r3 <= dst_val + src_val;
                        endcase
                        dout  <= dst_val + src_val;
                        phase <= 0;
                    end
                    4'h4: begin
                        pc    <= imm;
                        phase <= 0;
                    end
                    4'h5: begin
                        case (rd)
                            0: dout <= r0;
                            1: dout <= r1;
                            2: dout <= r2;
                            3: dout <= r3;
                        endcase
                        phase <= 0;
                    end
                    4'h6: begin
                        halted <= 1;
                        phase  <= 0;
                    end
                    default: begin
                        phase <= 0;
                    end
                endcase
            end
        end
    end

endmodule
