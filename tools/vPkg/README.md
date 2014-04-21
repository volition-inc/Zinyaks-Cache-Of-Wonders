# vPkg

The vpkg tool for SR4 is designed to allow creation of packfiles(vpp\_pc), compressed streaming files(str2\_pc) and asset assembler files(asm_pc). The tool supports extraction and building of the archives used in Saints Row 4.

Running the tool involves the command line so batch files can easily be created to accomplish tasks. The command line arguments are as follows:

<pre><code>USAGE: vpkg\_wd.exe /?
           -output_dir [dirname]
           -list_allocators
           -list_container_types
           -extract_asm [asm filename]
           -build_asm [asm filename]
           -build_str2 [str2 filename]
           -build_packfile [packfile filename] [filename ...]
           -extract_packfile filename
		   -update_str2 [str2 filename] [asm filename] [filename ...]
</code></pre>

Notes on vpkg commands:

* extract\_asm will convert an asm file into an xml file for editing
* build\_asm will convert an xml asm file to a binary asm file. This also supports creating new asm files from new/altered xml.

* output_dir is a global setting that affects the working directory for building and extracting asm, str2, and packfiles.  For example, when extracting a packfile, output\_dir will specify the output directory where the files within the packfile will be extracted.  When building a packfile, output\_dir specifies the directory where the built packfile will be placed.

* If output\_dir is not specified, extracted files will be located in the current working directory.