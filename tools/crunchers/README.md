# Crunchers

This folder contains several of the crunchers that will be needed to build new content for SR4.  All crunchers take a single filename as a command line option.  This filename is called a rule file and contains all the information that is needed to crunch a particular asset into its target format.  The rule files given are templates that can be used to build new rule files by hand.

Eventually, the Volition FBX converter should output rule files that don't need (much) modification.

Currently, the FBX tool might use absolute paths for sources and targets in the rule files.  In some cases, the crunchers will use the absolute path and then look for the file in the local folder.  The target tags will always output the target where the tag specifies.  Please make sure that you edit any rules before crunching to make sure that you are aware of what is happening.  As this project progresses, changes will be made so this type of editing should no longer be required.

The general format of running a cruncher is

<cruncher name> <rule file>

i.e.

texture_crunch_wd.exe blingshotgun_texture.rule

Currently, the following crunchers work:

* Texture Cruncher - used to crunch a source texture (i.e. targa file) into a platform specific vbm (Volition bitmap format)
* Peg Assembler - used to assemble vbm files into a platform specific peg file
* Rig Cruncher - used to crunch .rigx files into platform specific rig files

