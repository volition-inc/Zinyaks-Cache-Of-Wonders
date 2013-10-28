# vPkg

The vpkg tool for SR4 is designed to allow creation of packfiles(vpp_pc), compressed streaming files(sr2_pc) and asset assembler files(asm_pc). The tool supports extraction and building of the archives used in Saints Row 4.

Running the tool involves the command line so batch files can easily be created to accomplish tasks. The command line arguments are as follows:
- -working_dir <dirname>
- -list_allocators
- -list_container_types
- -extract_asm <asm_filename>
- -build_asm <asm_xml_filename>
- -build_packfile <packfile_name.vpp_pc> <-combine_asms combined_asm_name.asm_pc> <filename1> <filename2> …
- -extract_packfile <packfile_name.vpp_pc>

extract asm will convert an asm file into an xml file for editing
build asm will convert an xml asm file to a binary asm file. This also supports creating new asm files from new/altered xml.

working dir is a global setting that will make extract_packfile and build_packfile

Extracting a packfile will extract to the working dir or to the current working directory if working dir is not set and is able to extract vpp_pc and str2_pc files.
