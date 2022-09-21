# Converting Myisam Table to Aria Table

![Python](https://img.shields.io/badge/Python-3.9.12-ff69b4)
![MariaDB](https://img.shields.io/badge/MariaDB-10.6.9-blueviolet)

This repository is to convert all MariaDB tables in a specified database to Aria from Myisam

This python script is based on automating the SQL scripts located in [sql_scripts](sql_scripts). The obvious desire to automate this process was the motivation for the project

Lastly, the reason for doing this at all, is to convert tables in a MariaDB database to _Aria_ and update all _CHAR_ fields to _VARCHAR_. For changing the field data type, we needed to do this because as of version MariaDB: 10.6.9 there was a bug we were experiencing when changing the table type.

## Enviornment File

When making the `.env` file, make sure it has the below format.

```json:
user = USER_NAME
password = PASSWORD
database = 'information_schema'
host = HOST_ADDRESS
port = PORT_NUMBER
database_to_alter = DATABASE_TO_ALTER
```

### Creating `.env` File

From the root directory run the below in your command line, and then in the created file copy the above and fill in the neccessary data:

```
echo BLANK_ENVIORNMENT > python_scripts/.env22
```

## Software Versions

- Python: 3.9.12
- MariaDB: 10.6.9

### Anaconda packages install (Windows 10)

Replace `ENV_NAME` with the name you want for your enviornment and then run the below.

```bash:
conda create -n ENV_NAME python=3.9
conda activate ENV_NAME
conda install -n ENV_NAME --file requirements.txt
```