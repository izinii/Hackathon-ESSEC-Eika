
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






from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document

# Étape 3 : Charger les deux PDFs
print("\n\n\n\nEtape 3:")

# PDF loaders
loader1 = PyPDFLoader("Explanations_about_each_columns_of_the_clients_dataset.pdf")
loader2 = PyPDFLoader("The_different_types_of_insurance_contracts_and_details.pdf")
docs = loader1.load() + loader2.load()

# Chunking
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_documents(docs)
print(f"🧩 Chunks générés : {len(chunks)}")

# Embedding FAISS pour les PDF
embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_runtime)
vectorstore = FAISS.from_documents(chunks, embedding=embeddings)
pdf_retriever = vectorstore.as_retriever()
print("✅ Retriever PDF prêt via FAISS")




print("\n\n\n\nEtape 4:")
import boto3

# Bedrock Agent Runtime client (attention, pas bedrock-runtime ici !)
agent_runtime = boto3.client("bedrock-agent-runtime", region_name="us-west-2")

# Ton Knowledge Base ID
KB_ID = "D9HS1D1D2A"

# Ton modèle Titan
MODEL_ARN = "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-text-express-v1"

def query_redshift_kb(question):
    response = agent_runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KB_ID,
                "modelArn": MODEL_ARN
            }
        }
    )
    return response["output"]["text"]




# LLM Titan
llm = BedrockLLM(
    model_id="amazon.titan-text-express-v1",
    region_name="us-west-2",
    model_kwargs={
        "temperature": 0.3,
        "maxTokenCount": 2048,
        "topP": 0.9
    }
)

def hybrid_rag_answer(question):
    # 🔍 PDF via FAISS
    pdf_docs = pdf_retriever.get_relevant_documents(question)
    context_pdf = "\n\n".join([doc.page_content for doc in pdf_docs])

    # 🔍 Redshift KB via Bedrock
    redshift_kb_answer = query_redshift_kb(question)

    # 🧠 Fusion dans le prompt
    final_prompt = f"""Réponds à la question suivante en utilisant les deux sources :
    
### Contexte PDF :
{context_pdf}

### Réponse Redshift KB :
{redshift_kb_answer}

### Question :
{question}

Réponse :
"""

    # LLM
    response = llm.invoke(final_prompt)
    return response

# Exemple d’appel
question = "Quels types de contrats sont souscrits par les clients âgés de plus de 60 ans ?"
response = hybrid_rag_answer(question)
print("\n\nRéponse finale fusionnée :")
print(response)
