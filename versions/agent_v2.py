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
df_clients = df_clients.head(10)
print("DataFrame clients :")
print(f"Nombre de lignes : {len(df_clients)}")
print(df_clients)






# Étape 3 : Charger les deux PDFs dans un système RAG
print("\n\n\n\nEtape 3:")

# Charger les 2 fichiers PDF
loader1 = PyPDFLoader("Explanations_about_each_columns_of_the_clients_dataset.pdf")
loader2 = PyPDFLoader("The_different_types_of_insurance_contracts_and_details.pdf")

docs = loader1.load() + loader2.load()

print(f"✅ PDF chargés : {len(docs)} pages")

# Split en chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_documents(docs)

print(f"🧩 Chunks générés : {len(chunks)}")

# Embedding + FAISS
embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_runtime)
vectorstore = FAISS.from_documents(chunks, embedding=embeddings)
retriever = vectorstore.as_retriever()

print("✅ RAG prêt avec FAISS + Titan")









# Étape 4 : Lancer l’agent amazon.titan-text-express-v1 en mode RAG
print("\n\n\n\nEtape 4:")

llm = BedrockLLM(
    model_id="amazon.titan-text-express-v1",
    region_name="us-west-2",
    model_kwargs={
        "temperature": 0.3,
        "maxTokenCount": 2048,
        "topP": 0.9
    }
)

# Crée la chaîne RAG
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=False
)











# Étape 5 : Traitement des clients par batch avec filtrage intelligent
print("\n\n\n\nEtape 5:=== Traitement par batch en cours... ===")

import json

batch_size = 1
all_responses = []

for i in range(0, len(df_clients), batch_size):
    batch = df_clients.iloc[i:i+batch_size]
    records = batch.to_dict(orient="records")

    prompt = f"""
Tu es un conseiller IA expert en assurance. Voici {len(records)} clients.

Ta mission :
- Pour chaque client, regarde s'il faut ajuster un contrat existant ou en proposer un nouveau.
- Si tout va bien → ne rien dire.
- Sinon, indique :
    - Le Client_ID
    - Les raisons (valeurs + nom des colonnes)
    - Le contrat recommandé, selon les critères produits

Voici les clients (en JSON) :
{json.dumps(records, indent=2)}

Réponds uniquement pour les clients nécessitant un ajustement.
Formate ta réponse clairement, un par ligne.
"""

    try:
        response = qa_chain.invoke(prompt)
        print(f"\n🧠 Résultat batch {i // batch_size + 1} :")
        print(response)
        all_responses.append(response)
    except Exception as e:
        print(f"❌ Erreur batch {i // batch_size + 1} :", e)



import re
import csv

# Créer une liste structurée pour les lignes finales
structured_results = []

for block in all_responses:
    if isinstance(block, dict):
        block = block.get("result", "")
    elif not isinstance(block, str):
        continue

    # Séparer par clients (un client = un bloc commençant par "Client_ID")
    clients = re.split(r"\bClient_ID\s*[:：]\s*", block)
    for c in clients[1:]:  # on saute le premier (avant le premier Client_ID)
        lines = c.strip().splitlines()
        client_id = lines[0].strip()
        reasons = []
        contract = ""

        for line in lines[1:]:
            if "raison" in line.lower() or "reason" in line.lower():
                reasons.append(line.strip())
            if "contract" in line.lower():
                contract = line.strip()

        # On n'enregistre que si un contrat a été recommandé
        if contract:
            structured_results.append({
                "Client_ID": client_id,
                "Raisons": " | ".join(reasons),
                "Contrat recommandé": contract
            })


# Écriture propre en CSV
with open("recommandations_structurées.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Client_ID", "Raisons", "Contrat recommandé"])
    writer.writeheader()
    writer.writerows(structured_results)

print("\n✅ Export structuré terminé dans recommandations_structurées.csv")