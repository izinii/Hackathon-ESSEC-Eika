# Étape 1 : Setup

import boto3
import pandas as pd
import time
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings
from langchain_aws import BedrockLLM

# Client AWS    
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-west-2")
redshift_client = boto3.client("redshift-data", region_name="us-west-2")

# Redshift config
DATABASE = "dev"
WORKGROUP = "redshift-wg-hackathon"






# Étape 2 : Récupération des données Redshift

def get_redshift_data():
    query = "SELECT * FROM clients_database;"
    response = redshift_client.execute_statement(Database=DATABASE, WorkgroupName=WORKGROUP, Sql=query)
    statement_id = response["Id"]

    while True:
        status = redshift_client.describe_statement(Id=statement_id)
        if status["Status"] in ["FINISHED", "FAILED", "ABORTED"]:
            break
        time.sleep(1)

    results = redshift_client.get_statement_result(Id=statement_id)
    columns = [col["name"] for col in results["ColumnMetadata"]]
    rows = [
        [field.get("stringValue", "") for field in record]
        for record in results["Records"]
    ]
    return pd.DataFrame(rows, columns=columns)

df_clients = get_redshift_data()
#df_clients = df_clients.head(10)
print("DataFrame clients :")
print(f"Nombre de lignes : {len(df_clients)}")
print(df_clients)






# Étape 3 : Charger les deux PDFs dans un système RAG
print("\n\n\n\nEtape 3:")

# Identifiants
bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name="us-west-2")

# ID du Knowledge Base (vu sur ta capture)
knowledge_base_id = "D9HS1D1D2A"

def rag_query_to_knowledge_base(question: str):
    response = bedrock_runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
            }
        }
    )
    return response["output"]["text"]

# Exemple d’appel
question = "Quels sont les clients de plus de 60 ans ayant souscrit un contrat santé ?"
reponse = rag_query_to_knowledge_base(question)
print("Réponse de l'agent IA :")
print(reponse)

