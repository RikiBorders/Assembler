Yes, this was a college project.

# Assembler
A Python-based assembler capable of parsing and assembling SIC/XE assembly files.


In order to use the assembler, it must be called from the command line with two arguments, which
are the input and output file names. If, for example, the user wanted to assemble a file titled "program1.asm",
then they would call the assembler via command line like so: "rasm program1.asm program1.obj" (without quotations).
This would create an object file named program1.obj that contains all of the generated machine code from program1.asm.


This assembler handles the generation of machine code and parsing of SIX/XE instructions in two passes. Locations are
stored on pass 1, and bits are generated with respect to each saved location on pass 2.
