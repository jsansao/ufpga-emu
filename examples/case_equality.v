module case_equality(
    input [3:0] a, b,
    output eq, neq
);
    assign eq = (a === b);
    assign neq = (a !== b);
endmodule
