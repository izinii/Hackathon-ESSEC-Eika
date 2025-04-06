import sqlite3
import pandas as pd
import json
import time
import boto3


# === CONFIGURATION ===
DB_PATH = "users.db" # SQLite database to generate


client = boto3.client('redshift-data', region_name='us-west-2')
database = 'dev'
workgroup_name = 'redshift-wg-hackathon'


# === IMPORT THE DATABASE ===
def import_database(query):
    try:
        response = client.execute_statement(
            Database=database,
            WorkgroupName=workgroup_name,
            Sql=query
        )
        statement_id = response["Id"]

        while True:
            status = client.describe_statement(Id=statement_id)
            if status["Status"] in ["FINISHED", "FAILED", "ABORTED"]:
                break
            time.sleep(1)

        if status["Status"] == "FINISHED":
            results = client.get_statement_result(Id=statement_id)
            columns = [col["name"] for col in results["ColumnMetadata"]]
            rows = [
                [field.get("stringValue", "") for field in record]
                for record in results["Records"]
            ]
            df = pd.DataFrame(rows, columns=columns)
            return df
        else:
            print("Erreur :", status["Error"])
    except Exception as e:
        print("Exception :", e)

df = import_database("SELECT * FROM clients_database order by client_id;")



# === CREATE / RESET THE DATABASE ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS users")  # Cleaning
cursor.execute("""
    CREATE TABLE users (
        user_id NUMBER PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL,
        role VARCHAR(255) NOT NULL,
        data VARCHAR(255)
    )
""")

# === ADD ADMIN ===
cursor.execute("""
    INSERT INTO users (user_id, username, password, role, data)
    VALUES (?, ?, ?, ?, ?)
""", ("admin001", "advisor", "adminpass", "admin", None))

# === ADD ALL THE CUSTOMERS OF THE DATABASE ===
for _, row in df.iterrows():
    client_id = str(row["client_id"])
    username = f"user{client_id}"
    password = f"client{client_id}"
    role = "client"

    # Exclude Client_ID from stored data
    client_data = row.to_dict()
    client_data.pop("client_id", None)

    # Insertion
    cursor.execute("""
        INSERT INTO users (user_id, username, password, role, data)
        VALUES (?, ?, ?, ?, ?)
    """, (client_id, username, password, role, json.dumps(client_data)))



# === SAUVEGARDE ET FERMETURE ===
conn.commit()
conn.close()

print("users.db has been successfully generated !!!!")