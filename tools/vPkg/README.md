# vPkg

The vpkg tool for SR4 is designed to allow creation of packfiles(vpp\_pc), compressed streaming files(str2\_pc) and asset assembler files(asm_pc). The tool supports extraction and building of the archives used in Saints Row 4.

Running the tool involves the command line so batch files can easily be created to accomplish tasks. The command line arguments are as follows:

- -working\_dir &lt;dirname&gt;
- -list\_allocators
- -list\_container\_types
- -extract\_asm &lt;asm_filename&gt;
- -build\_asm &lt;asm\_xml\_filename&gt;
- -build\_packfile &lt;packfile\_name.vpp\_pc&gt; &lt;-combine\_asms combined\_asm\_name.asm\_pc&gt; &lt;filename1&gt; &lt;filename2&gt; ... 
- -extract\_packfile &lt;packfile\_name.vpp\_pc&gt;

extract asm will convert an asm file into an xml file for editing
build asm will convert an xml asm file to a binary asm file. This also supports creating new asm files from new/altered xml.

working dir is a global setting that will make extract\_packfile and build\_packfile

Extracting a packfile will extract to the working dir or to the current working directory if working dir is not set and is able to extract vpp\_pc and str2\_pc files.

