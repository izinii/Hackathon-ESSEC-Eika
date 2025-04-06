# Étape 1 : Imports et setup
import boto3
import pandas as pd
import time
import json
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings
from langchain_aws import BedrockLLM

# AWS clients
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-west-2")
redshift_client = boto3.client("redshift-data", region_name="us-west-2")

# Redshift config
DATABASE = "dev"
WORKGROUP = "redshift-wg-hackathon"

# Fonction d’appel Bedrock avec Claude 3.5 Haiku
def invoke_bedrock(prompt, model_id="anthropic.claude-3-5-haiku-20241022-v1:0", max_tokens=1024, temperature=0.3):
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    response = bedrock_runtime.invoke_model(
        body=json.dumps(body),
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

# Étape 2 : Charger les deux PDFs et préparer le retriever
print("=== Étape 2 : Chargement des PDFs ===")

loader1 = PyPDFLoader("Explanations_about_each_columns_of_the_clients_dataset.pdf")
loader2 = PyPDFLoader("The_different_types_of_insurance_contracts_and_details.pdf")
docs = loader1.load() + loader2.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_documents(docs)
print(f"🧩 {len(chunks)} chunks générés à partir des PDF")

embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_runtime)
vectorstore = FAISS.from_documents(chunks, embedding=embeddings)
pdf_retriever = vectorstore.as_retriever()
print("✅ Retriever FAISS prêt avec Titan Embeddings")

# Étape 3 : Fonction RAG Hybride
def hybrid_rag_answer(question, pdf_retriever, redshift_client, database, workgroup):
    # 🔍 PDF: FAISS
    pdf_docs = pdf_retriever.invoke(question)
    context_pdf = "\n---\n".join([doc.page_content for doc in pdf_docs[:3]])  # top 3 chunks

    # 🔍 Redshift : Génération requête SQL
    prompt_sql = f"Écris une requête SQL Redshift pour répondre à cette question :\n{question}\nTable cible : clients_database"
    generated_sql = invoke_bedrock(prompt_sql)
    print("\n📄 Requête SQL générée :")
    print(generated_sql)

    # 🔍 Exécution SQL Redshift
    try:
        response = redshift_client.execute_statement(
            Database=database,
            WorkgroupName=workgroup,
            Sql=generated_sql
        )
        statement_id = response["Id"]

        while True:
            status = redshift_client.describe_statement(Id=statement_id)
            if status["Status"] in ["FINISHED", "FAILED", "ABORTED"]:
                break
            time.sleep(1)

        results = redshift_client.get_statement_result(Id=statement_id)
        columns = [col["name"] for col in results["ColumnMetadata"]]
        rows = [[field.get("stringValue", "") for field in record] for record in results["Records"]]
        redshift_context = f"{columns}\n" + "\n".join(str(row) for row in rows)

    except Exception as e:
        redshift_context = f"[ERREUR SQL] : {str(e)}"

    # 🧠 Prompt final fusionné
    final_prompt = f"""Tu es un expert en analyse de données.

Voici les deux sources d'information :

📄 **Extrait de documents PDF** :
{context_pdf}

🛢️ **Données SQL issues de Redshift** :
{redshift_context}

Maintenant, réponds à la question suivante de manière claire et précise :

❓ {question}

Réponse :
"""
    return invoke_bedrock(final_prompt)

# Étape 4 : Test de la pipeline
if __name__ == "__main__":
    print("\n=== Étape 4 : Test final ===")
    question = "Quels sont les clients ayant plus de 60 ans et un contrat santé ?"
    answer = hybrid_rag_answer(
        question,
        pdf_retriever=pdf_retriever,
        redshift_client=redshift_client,
        database=DATABASE,
        workgroup=WORKGROUP
    )
    print("\n✅ Réponse finale :")
    print(answer)