import boto3
import os
import time
import json

session = boto3.Session()

# Étape 1 : Imports et setup
import boto3
import pandas as pd
import time
import json
from PyPDF2 import PdfReader
import smtplib
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor


# ---- AWS CONFIGURATION ----
AWS_REGION = "us-west-2"

# ---- REDSHIFT SERVERLESS CONFIGURATION ----
DATABASE = 'dev'  # nom de notre base de données
WORKGROUP_NAME = 'redshift-wg-hackathon'  # notre workgroup

# ---- INITIALISATION DES CLIENTS ----
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
redshift_client = boto3.client("redshift-data", region_name=AWS_REGION)






# ---- FONCTION POUR RÉCUPÉRER UN ÉCHANTILLON D'UNE TABLE ----
def get_table_sample():
    """Récupère 100 lignes d'une table Redshift pour analyse."""
    sql_query = f"SELECT * FROM clients_database WHERE Last_Account_Update = 1;"
    
    try:
        #print(f"🔄 Envoi de la requête à Redshift: {sql_query}")
        response = redshift_client.execute_statement(
            Database=DATABASE,
            WorkgroupName=WORKGROUP_NAME,
            Sql=sql_query
        )

        statement_id = response['Id']
        #print(f"✅ Requête envoyée, ID: {statement_id}")

        # Timeout après 60 secondes
        start_time = time.time()
        while True:
            status_response = redshift_client.describe_statement(Id=statement_id)
            status = status_response["Status"]

            if status in ["FINISHED", "FAILED", "ABORTED"]:
                break
            
            # Vérification du timeout (60 secondes max)
            if time.time() - start_time > 60:
                print("⏳ Timeout dépassé (60s). Annulation de la requête.")
                return "Timeout: La requête a pris trop de temps."

            #print("⏳ En attente des résultats...")
            time.sleep(3)  # Vérification toutes les 3 secondes

        if status == "FINISHED":
            #print("✅ Requête terminée, récupération des résultats...")
            result_response = redshift_client.get_statement_result(Id=statement_id)
            records = [
                ", ".join([col.get('stringValue', 'NULL') for col in row])
                for row in result_response.get("Records", [])
            ]
            return records if records else "Aucune donnée trouvée."
        else:
            print(f"❌ Erreur d'exécution: {status}")
            return f"Erreur lors de l'exécution: {status_response.get('Error', 'Erreur inconnue')}"

    except Exception as e:
        print(f"❌ Erreur de connexion ou d'exécution : {str(e)}")
        return f"Erreur : {str(e)}"
    




# ---- FONCTION POUR LIRE UN PDF ----
def load_pdf_text(path):
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    return text





# ---- FONCTION POUR CREER LE PROMPT ----
def create_prompt(client_rows, column_doc, contracts_doc):
    header = (
        "You are an AI agent working for an insurance company.\n"
        "You have access to:\n"
        "- the client data from the 'clients_database' table\n"
        "- a document explaining each column ('Explanations about each columns of the clients dataset')\n"
        "- a document describing the available insurance contracts and their eligibility criteria ('The different types of insurance contracts and details')\n\n"
        "For each client below, identify the most suitable insurance contract based on their data and the criteria described. "
        "Return the results in the following format:\n\n"
        "- Client_ID: <ID>\n"
        "- Reasons: <Value> (<ColumnName>), ...\n"
        "- Suggested Contract: <Contract Name>\n\n"
    )

    client_data_section = "\n=== Client Data ===\n"
    for row in client_rows:
        client_data_section += f"{row}\n"

    docs_section = "\n=== Column Documentation ===\n" + column_doc
    contracts_section = "\n=== Contract Descriptions ===\n" + contracts_doc

    return header + client_data_section + docs_section + contracts_section








# ---- FONCTION POUR CREER L'AGENT ----
def analyze_clients_with_claude():
    client_rows = get_table_sample()
    if not isinstance(client_rows, list):
        print("❌ Erreur dans la récupération des clients.")
        return

    columns_text = load_pdf_text("Explanations_about_each_columns_of_the_clients_dataset.pdf")
    contracts_text = load_pdf_text("The_different_types_of_insurance_contracts_and_details.pdf")

    prompt = create_prompt(client_rows, columns_text, contracts_text)

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 3000,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        #print("📤 Envoi à Claude 3.5 Haiku via Bedrock...")
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
            body=json.dumps(request_body)
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']

    except Exception as e:
        print(f"❌ Erreur avec Claude : {e}")
        return f"Erreur : {str(e)}"
    



result = analyze_clients_with_claude()
print(result)