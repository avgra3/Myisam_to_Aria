import mysql.connector as mariadb
from decouple import config

# Ask which database we want to show - note this is not the same as the the .env database
# database_to_alter = input("What database would you like to make an alter script for? ")
database_to_alter = config("database_to_alter", default="")
database = config("database", default="")

# Optimize
optimize = f"""SELECT CONCAT("OPTIMIZE TABLE ", GROUP_CONCAT(CONCAT('{database_to_alter}',".`",`TABLES`.TABLE_NAME,"` ") SEPARATOR ", "),";") AS "Combined Opimize"
        FROM {database}.`TABLES`
        WHERE `TABLES`.TABLE_SCHEMA='{database_to_alter}'
        AND TABLE_TYPE<>'VIEW'; """

# Alter/Change to Aria & char to var
alter_tables = f"""WITH combo_column AS (
	SELECT '{database_to_alter}' AS "TABLE_SCHEMA", a.TABLE_NAME AS "mod_table", a.TABLE_TYPE, b.DATA_TYPE,b.COLUMN_NAME,b.COLUMN_TYPE, b.COLUMN_DEFAULT,
	TRIM(TRAILING "," FROM
	GROUP_CONCAT(
	IFNULL(
	CONCAT("MODIFY COLUMN `",b.COLUMN_NAME,"` ",'var', b.COLUMN_TYPE, " CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT ", IFNULL(b.COLUMN_DEFAULT IS NULL, "NULL")), ""
	)
	SEPARATOR ",")) AS "column_update"
	FROM {database}.`TABLES` a INNER JOIN {database}.`COLUMNS` b
		ON a.TABLE_NAME = b.TABLE_NAME
			AND a.TABLE_SCHEMA = b.TABLE_SCHEMA
	WHERE a.TABLE_SCHEMA='{database_to_alter}'
		AND a.TABLE_SCHEMA = b.TABLE_SCHEMA
		AND a.TABLE_TYPE<>'VIEW'
		AND b.DATA_TYPE LIKE 'char%'
	GROUP BY a.TABLE_NAME
	),
	to_aria AS (
	SELECT '{database_to_alter}' AS "TABLE_SCHEMA", TABLE_NAME AS "mod_table", TABLE_TYPE, `TABLES`.`ENGINE`, CONCAT("ENGINE = Aria row_format=PAGE page_checksum=1 TRANSACTIONAL=0") AS "to_aria_engine"
	FROM {database}.`TABLES`
	WHERE `TABLES`.TABLE_SCHEMA='{database_to_alter}'
		AND (`TABLES`.`ENGINE`<>'Aria'
			OR `TABLES`.`ENGINE`='Myisam'))

    SELECT
	CONCAT("ALTER TABLE ",'{database_to_alter}',".`",a.TABLE_NAME,"` ",
	IFNULL(c.column_update, ""),
	IFNULL(d.to_aria_engine, ""),
	";") AS "Alter_Script"

    FROM {database}.`TABLES` a INNER JOIN {database}.`COLUMNS` b
	ON a.TABLE_NAME = b.TABLE_NAME
		AND a.TABLE_SCHEMA = b.TABLE_SCHEMA
		LEFT JOIN combo_column c
			ON a.TABLE_NAME = c.mod_table
				AND a.TABLE_SCHEMA = c.TABLE_SCHEMA
					LEFT JOIN to_aria d
						ON a.TABLE_NAME = d.mod_table
						 AND a.TABLE_SCHEMA = d.TABLE_SCHEMA

    WHERE a.TABLE_SCHEMA='{database_to_alter}'
        AND ((a.TABLE_NAME = c.mod_table AND a.TABLE_SCHEMA = c.TABLE_SCHEMA) OR (a.TABLE_NAME = d.mod_table AND a.TABLE_SCHEMA = d.TABLE_SCHEMA))
    GROUP BY a.TABLE_NAME;"""

# Connection String
connection = mariadb.connect(
    user=config("user", default=""),
    password=config("password", default=""),
    database=config("database", default=""),
    host=config("host", default=""),
    port=config("port", default=""),
)

# Function for getting which tables need to be updated
def combined_query(query: str, connection) -> list:
    try:
        cur = connection.cursor()
        cur.execute(query)

        # Returns a list
        combo_scripts = cur.fetchall()
        return combo_scripts

    except Exception as err:
        print(f"Error has occured: {err}")
        # Return an empty list
        return []

    finally:
        # Close the connection
        cur.close()
        print("Database connection has been closed")


# Function for running multiple scripts
def alter(state: str, connection, msg: str = "Done!"):
    try:
        cur = connection.cursor()
        result = cur.execute(state, multi=True)
        result.send(None)
        print(msg, result)

    except Exception as err:
        print(f"Error has occured: {err}")

    finally:
        # Close the connection
        cur.close()
        print("Database connection has been closed")


try:
    alter_table = combined_query(alter_tables, connection)
    print("Beginning Alter script...")
    for row in alter_table:
        alter(row[0], connection)

    print("Beginning Optimize script...")
    optimize_table = combined_query(optimize, connection)
    alter(optimize_table[0], connection)
    connection.commit()

except Exception as e:
    connection.rollback()
    connection.close()
    raise e
