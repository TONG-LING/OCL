Oracle Recover Command Line Tool (OCL)

It has only been tested on Windows and Linux in 11.2.0.4 and includes the following features:

![image](https://github.com/user-attachments/assets/00d684ef-bee6-4e08-9b5e-1899af0c4484)


1. When the software is started, the 'scan' command is automatically executed, and the database version number and byte order (storage) are output.
<img width="684" alt="2cde2dd6edfbfcae71d421c55d011a6" src="https://github.com/user-attachments/assets/e63f186f-0b13-4b14-9ae7-d552ee74bbe8" />


3. Then use the 'link' function to link the database control file and system.dbf file, so as to obtain the data file path, corresponding scn number and resetlog scn and other information.
<img width="529" alt="49a78aa9a4db3db17bb93dd80e43e6f" src="https://github.com/user-attachments/assets/45255e78-c209-4255-9af8-59bb15a440af" />


4. The 'link' function also provides a separate link in case the data file is incomplete, such as link user01.dbf.

![image](https://github.com/user-attachments/assets/4c7719be-4dfb-4ac5-8649-fbac26326cd4)

5.Use the 'info' command to view the current database information in real time

6. Use the 'recover datafile [fno]' command to recover the header block of the datafile (need to specify the corresponding reference file, because the modified content is extracted from the healthy datafile), for example:

ORA-01190: control file or data file x is from before the last RESETLOGS

ORA-01113: file x needs media recovery

...

<img width="1002" alt="13aa51475de7295923629eb6fd3b1c4" src="https://github.com/user-attachments/assets/66192480-76c4-4183-b2d4-fdc40233864f" />



7.The recover command also provides the function of recovering bad blocks by using 'recover block 4,1' (file no. 4, block No. 1), such as block check value errors:

![image](https://github.com/user-attachments/assets/1254bf9d-7310-4985-b582-5277ea1136f5)


8. Use the 'pscn' function (Log in as an administrator) to push the scn number in the database memory, such as ora-600[2662].

<img width="1079" alt="8cb32cd284b49715fee26248938ace0" src="https://github.com/user-attachments/assets/29792106-8696-49dc-ab35-81c62fbed3b4" />
