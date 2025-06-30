Oracle Recovery Command Line Tool (OCL)


📌 Overview

OCL is a professional command-line tool for Oracle database recovery, supporting both Windows and Linux platforms (tested on Oracle 11.2.0.4).

```bash
OCL >  help
```

![image](https://github.com/user-attachments/assets/28a5ae3d-354c-475a-a44a-a9f6fae18ef5)


⚠️ Important Notes:

All datafiles and control files must reside in system files
ASM storage is not currently supported
🛠 Key Features
🔍 1. Automatic Database Scan
![image](https://github.com/user-attachments/assets/b1abc435-0221-452a-a554-addb51786540)



Automatically detects database version
Displays byte order (endian) information
🔗 2. Database Linking

```bash
OCL >  link
```
![image](https://github.com/user-attachments/assets/bae5c0c8-b75d-4972-8c68-4579eca17708)

Connects control files with system.dbf
Retrieves:
Datafile paths
SCN numbers
Resetlog SCN information...

Partial Link Support:

![image](https://github.com/user-attachments/assets/4decabf4-d424-4684-ac82-90e8e584fe68)


ℹ️ 3. Real-time Database Information

```bash
OCL >  info
```

![image](https://github.com/user-attachments/assets/a3dc9668-c80b-41df-b235-1ab9535dad7d)


🩹 4. Datafile Recovery

```bash
OCL >  recover datafile [fno]
```

![image](https://github.com/user-attachments/assets/aa22eba9-b193-4a49-91b4-534607569246)


Repairs header blocks using reference files
Resolves:
ORA-01190 (control file issues)
ORA-01113 (media recovery required)


🧱 5. Block-level Recovery:  recover block 4,1

```bash
OCL >  recover block 4,1
```

![image](https://github.com/user-attachments/assets/a83169f4-ea1e-49d4-8587-7aea86f86a9c)



Repairs corrupted blocks
Fixes checksum errors


⏫ 6. SCN Management (Admin Only): 

```bash
OCL >  pscn
```

![image](https://github.com/user-attachments/assets/c986ac81-ac3e-45b4-869b-d77e4db946c2)
Resolves ORA-600[2662], errors
Updates SCN in database memory (oradebug)


📞 Contact
For database technology discussions and knowledge sharing:

Platform	ID
WeChat	wufachuji666
QQ	565929593
💡 All screenshots show actual recovery scenarios from production environments
