import boto3
import json
import pandas as pd
import time
from PyPDF2 import PdfReader
import smtplib
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor



# ---------- Bedrock Client ----------
def invoke_bedrock(prompt, model_id, max_tokens=5000, temperature=0.7):
    session = boto3.Session(profile_name="assurflow", region_name="us-west-2")
    client = session.client("bedrock-runtime")

    if "anthropic" in model_id:
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    else:
        raise ValueError("Unsupported model - only Claude is allowed in this version.")

    response = client.invoke_model(
        body=json.dumps(body),
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )
    result = json.loads(response['body'].read())
    return result["content"][0]["text"]






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



# ---------- Prompt Generator ----------
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



# ---------- Agent Wrapper ----------
def agent_runner(agent_id, model_id, profile, pdf_text):

    client_rows = get_table_sample()
    print(client_rows)
    if not isinstance(client_rows, list):
        print("❌ Erreur dans la récupération des clients.")
        return

    columns_text = load_pdf_text("Explanations_about_each_columns_of_the_clients_dataset.pdf")
    contracts_text = load_pdf_text("The_different_types_of_insurance_contracts_and_details.pdf")

    prompt = create_prompt(client_rows, columns_text, contracts_text)





    prompt = create_prompt(profile, pdf_text)
    print(f"Running Agent {agent_id}...")
    try:
        response = invoke_bedrock(prompt, model_id)
    except Exception as e:
        print(f"[{agent_id}] Bedrock error: {e}")
        response = {'error': 'model access denied or failure'}
    return agent_id, response



# ---------- Agent B (Consensus Synthesizer) ----------
def agent_b_consensus(a1_output, a2_output):
    prompt = f"""
You are a senior insurance recommendation reviewer.
Two independent AI agents (A1 and A2) have provided suggestions for a client.

Your job is to synthesize both outputs and determine the best unified recommendation.

Only respond if at least one agent made a recommendation.
Output format:
"Final Recommendation: ..."
"Reasoning: ..."

---
Agent A1 Output:
{a1_output}

---
Agent A2 Output:
{a2_output}
"""
    print("\nRunning Agent B (Consensus)...")
    return invoke_bedrock(prompt, "anthropic.claude-3-5-haiku-20241022-v1:0")



# ---------- Agent D (Message Generator) ----------
def agent_d_generate_message(final_reco):
    prompt = f"""
You are a professional assistant writing emails for an insurance advisor.

Based on the following recommendation, draft a short, clear and professional message that can be sent to the insurance company.

Recommendation Summary:
{final_reco}

The message should:
- Be in English
- Address the insurer formally
- Mention the client's needs briefly
- Suggest a product or adjustment
- Be polite and clear

Output only the email body.
"""
    print("\nRunning Agent D (Message Generator)...")
    return invoke_bedrock(prompt, "anthropic.claude-3-5-haiku-20241022-v1:0")



# ---------- Email Sender via MailHog ----------
def send_email_mailhog(sender_email, recipient_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    print("\nSending email via MailHog SMTP on localhost:1025...")
    try:
        with smtplib.SMTP('localhost', 1025) as server:
            server.sendmail(sender_email, [recipient_email], msg.as_string())
        print("Email successfully sent to MailHog inbox.")
    except Exception as e:
        print("Failed to send email via MailHog:", str(e))



# ---------- Main Entry Point ----------
def run_agents_on_profile(csv_path, pdf_path, row_index=0):
    df = pd.read_csv(csv_path)
    profile = df.iloc[row_index:row_index+1].to_dict(orient="records")  # Single client as list of dict
    #pdf_text = extract_pdf_text(pdf_path)

    agents = {
        "A1": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "A2": "anthropic.claude-3-5-haiku-20241022-v1:0"
    }

    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(agent_runner, aid, mid, profile, pdf_text) for aid, mid in agents.items()]
        for future in futures:
            agent_id, output = future.result()
            results[agent_id] = output

    # Run Agent B
    a1_output = results.get("A1", "")
    a2_output = results.get("A2", "")
    consensus = agent_b_consensus(a1_output, a2_output)
    results["B"] = consensus

    # Run Agent D
    message_body = agent_d_generate_message(consensus)
    results["D"] = message_body

    # Send email via MailHog (localhost:1025)
    send_email_mailhog(
        sender_email="assurflow@example.com",
        recipient_email="insurer@example.com",
        subject="[AssurFlow] Recommendation for client profile",
        body=message_body
    )

    return results



# ---------- Example Usage ----------
if __name__ == "__main__":
    csv_path = "final_insurance_data.csv"
    pdf_path = "assurance_offers.pdf"

    results = run_agents_on_profile(csv_path, pdf_path, row_index=0)

    for agent_id, output in results.items():
        print(f"\n=== {agent_id} ===\n{output}")
