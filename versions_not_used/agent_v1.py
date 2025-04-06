import boto3
import json

session = boto3.Session(profile_name="default", region_name="us-west-2")

# --------------------------------------------------------------------------------------------


"""
# Appel à Bedrock Runtime
bedrock_runtime = session.client("bedrock-runtime")

prompt = {
    "inputText": "What's something cool about AI?"
}

payload = json.dumps(prompt)

response = bedrock_runtime.invoke_model(
    modelId="amazon.titan-text-express-v1",
    body=payload.encode("utf-8"),
    contentType="application/json",
    accept="application/json"
)

# Récupération et parsing de la réponse JSON
result_raw = response["body"].read()
result_json = json.loads(result_raw)

# 🌟 Affichage structuré de toutes les infos
print("\n=== 📊 Résultat complet de Titan ===\n")

print(f"🔢 Tokens en entrée : {result_json.get('inputTextTokenCount', 'N/A')}")
print(f"🔢 Tokens en sortie : {result_json['results'][0].get('tokenCount', 'N/A')}")
print(f"✅ Raison de fin : {result_json['results'][0].get('completionReason', 'N/A')}")
print("\n🧠 Réponse du modèle :\n")
print(result_json['results'][0].get('outputText', '').strip())
"""

# --------------------------------------------------------------------------------------------

# Étape 1 : Setup

import boto3
import pandas as pd
import time
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
from langchain_aws import BedrockLLM
from langchain.docstore.document import Document

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
print("DataFrame clients :")
print(f"Nombre de lignes : {len(df_clients)}")
print(df_clients)







# Étape 3 : Charger les deux PDFs et la base de données dans un système RAG
print("\n\n\n\n")

import os
from langchain.docstore.document import Document
from langchain_aws import BedrockEmbeddings  # version à jour ✅

# Charger les 2 fichiers PDF
loader1 = PyPDFLoader("Explanations_about_each_columns_of_the_clients_dataset.pdf")
loader2 = PyPDFLoader("The_different_types_of_insurance_contracts_and_details.pdf")

docs = loader1.load() + loader2.load()
print(f"✅ PDF chargés : {len(docs)} pages")

# 🔁 Sélectionner les 1000 premiers clients uniquement
df_clients_sample = df_clients.head(1000)

# 🔁 Ajouter les clients dans le corpus RAG
def clients_to_documents(df):
    docs = []
    for _, row in df.iterrows():
        content = "\n".join([f"{col} : {row[col]}" for col in df.columns])
        doc = Document(page_content=content, metadata={"source": "clients_database"})
        docs.append(doc)
    return docs

client_docs = clients_to_documents(df_clients_sample)
docs += client_docs

# ✅ Chemin de l'index sauvegardé
faiss_path = "faiss_index/"

# Embeddings avec classe officielle (langchain_aws)
embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v1",
    region_name="us-west-2"
)

# ⚡️ Sauvegarde / chargement automatique de FAISS
if os.path.exists(faiss_path):
    print("📦 Index FAISS déjà existant, chargement en cours...")
    vectorstore = FAISS.load_local(faiss_path, embeddings)
else:
    print("🧠 Création du FAISS à partir des documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(docs)
    print(f"🧩 Total chunks générés : {len(chunks)}")
    
    vectorstore = FAISS.from_documents(chunks, embedding=embeddings)
    vectorstore.save_local(faiss_path)
    print(f"✅ Index FAISS sauvegardé à l’emplacement : {faiss_path}")

retriever = vectorstore.as_retriever()
print("✅ RAG prêt avec FAISS + Titan + Clients")









# Étape 4 : Lancer l’agent amazon.titan-text-express-v1 en mode RAG
print("\n\n\n\n")

# 🔎 TEST : recherche de clients à risque avec revenu faible
from langchain.chains import RetrievalQA
from langchain_aws import BedrockLLM  # version à jour

# Initialise Titan Text Express
llm = BedrockLLM(
    model_id="amazon.titan-text-express-v1",
    region_name="us-west-2",
    model_kwargs={
        "temperature": 0.3,
        "maxTokenCount": 2048,
        "topP": 0.9
    }
)

# Créer la chaîne RAG
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=False
)

# 🔍 Prompt de test
prompt_test = """
Quels clients parmi la base sont à risque élevé et pourraient avoir besoin d'un ajustement de contrat ?
Réponds uniquement s'il y a un besoin de changement, avec leur Client_ID, et les raisons.
"""

response = qa_chain.invoke(prompt_test)

print("\n🔎 RÉPONSE DE L'AGENT A1 (TEST)")
print(response)





















