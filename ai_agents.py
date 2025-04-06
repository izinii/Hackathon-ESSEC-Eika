import boto3
import time
import json
from PyPDF2 import PdfReader
from concurrent.futures import ThreadPoolExecutor
import smtplib
from email.mime.text import MIMEText


# ---- CONFIGURATION AWS ----
AWS_REGION = "us-west-2"
DATABASE = 'dev'
WORKGROUP_NAME = 'redshift-wg-hackathon'

# ---- INITIALISATION DES CLIENTS ----
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
redshift_client = boto3.client("redshift-data", region_name=AWS_REGION)



# ---- FONCTION POUR RÉCUPÉRER UN ÉCHANTILLON ----
def get_table_sample():
    sql_query = "SELECT * FROM clients_database WHERE Last_Account_Update = 1;"
    try:
        response = redshift_client.execute_statement(
            Database=DATABASE,
            WorkgroupName=WORKGROUP_NAME,
            Sql=sql_query
        )
        statement_id = response['Id']
        start_time = time.time()
        while True:
            status_response = redshift_client.describe_statement(Id=statement_id)
            status = status_response["Status"]
            if status in ["FINISHED", "FAILED", "ABORTED"]:
                break
            if time.time() - start_time > 60:
                return "Timeout: La requête a pris trop de temps."
            time.sleep(3)
        if status == "FINISHED":
            result_response = redshift_client.get_statement_result(Id=statement_id)
            records = [
                ", ".join([col.get('stringValue', 'NULL') for col in row])
                for row in result_response.get("Records", [])
            ]
            return records if records else "Aucune donnée trouvée."
        else:
            return f"Erreur : {status_response.get('Error', 'Erreur inconnue')}"
    except Exception as e:
        return f"Erreur : {str(e)}"



# ---- LECTURE DE PDF ----
def load_pdf_text(path):
    reader = PdfReader(path)
    return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())



# ---- GÉNÉRATION DU PROMPT ----
def create_prompt(client_rows, column_doc, contracts_doc):
    header = (
        "You are an AI agent working for an insurance company.\n"
        "You have access to:\n"
        "- the client data from the 'clients_database' table\n"
        "- a document explaining each column\n"
        "- a document describing the available insurance contracts and their eligibility criteria\n\n"
        "For each client below, identify the most suitable insurance contract based on their data and the criteria described. "
        "Return the results in the following format:\n\n"
        "- Client_ID: <ID>\n"
        "- Reasons: <Value> (<ColumnName>), ...\n"
        "- Suggested Contract: <Contract Name>\n\n"
    )

    client_data_section = "\n=== Client Data ===\n"
    for row in client_rows:
        client_data_section += f"{row}\n"

    docs_section = "\n=== Column Documentation ===\n" + column_doc[:2000]
    contracts_section = "\n=== Contract Descriptions ===\n" + contracts_doc[:3000]

    return header + client_data_section + docs_section + contracts_section



# ---- INVOCATION DE CLAUDE ----
def invoke_claude(prompt, temperature=0.3, model_id="anthropic.claude-3-5-haiku-20241022-v1:0"):
    print("🚀 Running Agent A1 (Claude)...")
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 3000,
        "temperature": temperature,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            accept="application/json",
            contentType="application/json"
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        return f"[Claude] Error: {str(e)}"



# ---- INVOCATION DE MISTRAL ----
def invoke_mistral(prompt, temperature=0.5, model_id="mistral.mistral-large-2407-v1:0"):
    print("🚀 Running Agent A2 (Mistral)...")
    request_body = {
        "prompt": prompt,
        "max_tokens": 1000,
        "temperature": temperature,
        "top_p": 0.9,
        "stop": []
    }
    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            accept="application/json",
            contentType="application/json"
        )
        result = json.loads(response['body'].read())
        
        # ✅ Correction ici
        if "generation" in result:
            return result["generation"]
        elif "outputs" in result:
            return result["outputs"][0]["text"]
        else:
            return "[Mistral] Unexpected response format: " + json.dumps(result)

    except Exception as e:
        return f"[Mistral] Error: {str(e)}"



# ---- LANCEMENT DES AGENTS A1 & A2 ----
def run_agents_a1_claude_a2_mistral():
    client_rows = get_table_sample()
    if not isinstance(client_rows, list):
        print("Erreur dans la récupération des clients.")
        return

    columns_text = load_pdf_text("Explanations_about_each_columns_of_the_clients_dataset.pdf")
    contracts_text = load_pdf_text("The_different_types_of_insurance_contracts_and_details.pdf")
    prompt = create_prompt(client_rows, columns_text, contracts_text)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            "A1 (Claude)": executor.submit(invoke_claude, prompt, 0.3),
            "A2 (Mistral)": executor.submit(invoke_mistral, prompt, 0.5)
        }
        results = {agent: future.result() for agent, future in futures.items()}

    return results

def run_agent_b_consensus(a1_output, a2_output):
    print("🧠 Running Agent B (Consensus Synthesizer)...")

    prompt = f"""
You are Agent B, a senior insurance decision reviewer.

You receive two independent contract recommendation reports for the same clients:
- Agent A1 (Claude): {a1_output}
- Agent A2 (Mistral): {a2_output}

Your task:
For each client mentioned, compare both agents’ recommendations.

If both agents suggest the same contract (even phrased differently), confirm it.

If the recommendations differ:
- Analyze both rationales
- Select the most appropriate recommendation
- Explain why you chose one over the other

Format:
Client_ID: <ID>
Final Contract: <chosen contract>
Reasoning: <why this contract was chosen over the other or confirmed>
"""

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
            body=json.dumps(request_body),
            accept="application/json",
            contentType="application/json"
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        return f"[Agent B] Error: {str(e)}"


def run_agent_c_verifier(consensus_output, client_data, column_doc, contracts_doc):
    print("🔎 Running Agent C (Reverse Engineering Auditor)...")

    prompt = f"""
You are Agent C, an independent insurance auditor AI.

Your task:
Given a final recommendation for each client, re-verify it **from scratch** using only the client's data, the column descriptions, and the insurance contract details.

You must reverse engineer the logic:
- Does the final recommendation make sense based on the data?
- If YES → Confirm it and explain briefly why.
- If NO → Reject it, and propose a more suitable alternative with reasoning.

Here is the final recommendation to validate:
{consensus_output}

=== Client Data ===
{json.dumps(client_data, indent=2)}

=== Column Documentation ===
{column_doc[:2000]}

=== Insurance Contracts ===
{contracts_doc[:3000]}
"""

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2500,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
            body=json.dumps(request_body),
            accept="application/json",
            contentType="application/json"
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        return f"[Agent C] Error: {str(e)}"
    

def run_agent_d_generate_email(consensus_output):
    print("✉️ Running Agent D (Email Generator)...")

    prompt = f"""
You are a professional assistant writing emails for an insurance advisor.

Based on the following summary of final insurance recommendations, write a short, clear and professional message that can be sent to the insurance company.

Summary:
{consensus_output}

The email must:
- Be in English
- Address the insurer formally
- Mention the clients' situations briefly
- Suggest products or contract adjustments clearly
- Be polite and professional

Only return the **email body**, no greeting or signature.
"""

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 800,
        "temperature": 0.4,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
            body=json.dumps(request_body),
            accept="application/json",
            contentType="application/json"
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        return f"[Agent D] Error: {str(e)}"

def send_email_mailhog(sender_email, recipient_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    print("\n📤 Sending email via MailHog SMTP on localhost:1025...")
    try:
        with smtplib.SMTP('localhost', 1025) as server:
            server.sendmail(sender_email, [recipient_email], msg.as_string())
        print("✅ Email successfully sent to MailHog inbox.")
    except Exception as e:
        print("❌ Failed to send email via MailHog:", str(e))




def final_run(): 
    # Lancer A1 et A2 en parallèle
    results = run_agents_a1_claude_a2_mistral()

    print(f"\n===== A1 (Claude) =====\n{results['A1 (Claude)']}")
    print(f"\n===== A2 (Mistral) =====\n{results['A2 (Mistral)']}")

    # Agent B : Synthèse des deux
    consensus = run_agent_b_consensus(results['A1 (Claude)'], results['A2 (Mistral)'])
    print(f"\n===== Agent B (Consensus) =====\n{consensus}")

    # Charger les données nécessaires pour l'audit par Agent C
    client_rows = get_table_sample()
    column_doc = load_pdf_text("Explanations_about_each_columns_of_the_clients_dataset.pdf")
    contracts_doc = load_pdf_text("The_different_types_of_insurance_contracts_and_details.pdf")

    # Agent C : Validation inverse (reverse engineering)
    agent_c_output = run_agent_c_verifier(
        consensus_output=consensus,
        client_data=client_rows,
        column_doc=column_doc,
        contracts_doc=contracts_doc
    )

    print(f"\n===== Agent C (Reverse Validator) =====\n{agent_c_output}")

    # Agent D : Email professionnel basé sur les recommandations de B
    email_body = run_agent_d_generate_email(consensus)
    print(f"\n===== Agent D (Email Message) =====\n{email_body}")

    # Envoi simulé de l’email via MailHog
    send_email_mailhog(
        sender_email="assurflow@example.com",
        recipient_email="insurer@example.com",
        subject="[AssurFlow] Final recommendations for insurance adjustments",
        body=email_body
    )


    return {
        "A1 (Claude)": results.get("A1 (Claude)", ""),
        "A2 (Mistral)": results.get("A2 (Mistral)", ""),
        "Consensus": consensus,
        "Agent C": agent_c_output,
        "Email": email_body
    }





if __name__ == "__main__":
    final_run()