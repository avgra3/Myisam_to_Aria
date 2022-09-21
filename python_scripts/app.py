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
	GROUP_CONCAT(
	CONCAT(" MODIFY COLUMN `",b.COLUMN_NAME,"` ",'var', b.COLUMN_TYPE, " CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT ", IF(b.COLUMN_DEFAULT IS NULL, "NULL", b.COLUMN_DEFAULT))
	SEPARATOR ",") AS "column_update"
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
	IFNULL(CONCAT(c.column_update, ", "), ""),
	IFNULL(d.to_aria_engine, ""),
	"; OPTIMIZE TABLE ",'{database_to_alter}',".`", a.TABLE_NAME,"`;") AS "Alter_Script"

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


def combined_query(
    query: str, connection: mysql.connector.connection_cext.CMySQLConnection
) -> list:
    """_summary_

    Args:
        query (str): A string in the format for valid SQL querries.
        connection (mysql.connector.connection_cext.CMySQLConnection): A connection object which we use to access our database

    Returns:
        list: Returns a list for each of the created scripts.
    """
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
def alter(
    state: str,
    connection: mysql.connector.connection_cext.CMySQLConnection,
    msg: str = "Done!",
) -> None:
    """With a given connection, run a SQL script on a database and show a message when script has completed.

    Args:
        state (str): A single SQL script we will run in order to execute a script on our database.
        connection (mysql.connector.connection_cext.CMySQLConnection): Connection object which establishes the connection to the database.
        msg (str, optional): Output message string used to convey information. Defaults to "Done!".
    """

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


# Running our scripts
try:
    alter_table = combined_query(alter_tables, connection)
    for row in alter_table:
        alter(row[0])
    optimize_table = combined_query(optimize, connection)
    for row in optimize_table:
        alter(row[0])
    connection.commit()

except Exception as e:
    connection.rollback()
    raise e
