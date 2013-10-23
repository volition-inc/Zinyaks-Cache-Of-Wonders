# vehicle_table_crunch

The vehicle table crunch tool for Saints Row is designed to allow creation of cvtf files from the vehicle xml table files. It takes command line arguments to tell it where to find the vehicle table, vehicle variant table, and the customization table. It also takes an optional parameter to specify a directory for the output.

Running the tool involves the command line so batch files can easily be created to accomplish tasks.

Example command line:

vehicle_table_crunch.exe -working_dir my_mod -vehicle my_mod\tables\bike_broomstick01_veh.xtbl -cust_table my_mod\cust_tables\bike_broomstick01_cust.xtbl -variant_table my_mod\variants\vehicles\bike_broomstick01.xtbl
