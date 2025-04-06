import boto3
import json
import pandas as pd
import PyPDF2
from concurrent.futures import ThreadPoolExecutor

# ---------- Bedrock Client ----------
def invoke_bedrock(prompt, model_id, max_tokens=1024, temperature=0.7):
    session = boto3.Session(profile_name="assurflow", region_name="us-west-2")
    client = session.client("bedrock-runtime")

    if "anthropic" in model_id:
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    elif "titan" in model_id:
        body = {"inputText": prompt}
    elif "mistral" in model_id or "meta" in model_id:
        body = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    else:
        raise ValueError("Unsupported model")

    response = client.invoke_model(
        body=json.dumps(body),
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )
    result = json.loads(response['body'].read())

    if "anthropic" in model_id:
        return result["content"][0]["text"]
    elif "titan" in model_id:
        return result.get("results", [{}])[0].get("outputText", "[No output]")
    elif "mistral" in model_id or "meta" in model_id:
        if "outputs" in result:
            text = result["outputs"][0]["text"]
            if text.strip().startswith("```json"):
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                return text[json_start:json_end]
            return text
        else:
            return json.dumps(result)
    return result

# ---------- PDF Reader ----------
def extract_pdf_text(pdf_path):
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

# ---------- Prompt Generator ----------
def generate_prompt(profile, pdf_text):
    return f"""
You are an AI insurance advisor expert. You have been given information on 1 client.

Your mission:

- For the client, determine whether to adjust an existing insurance policy or recommend a new one.
- If everything looks good → do not respond.
- Otherwise, provide:
  - The Client_ID
  - The reasons (including the column names and their values)
  - The recommended insurance contract, based on product criteria

Client profile (in JSON):
{json.dumps(profile, indent=2)}

Insurance product details:
{pdf_text}

Only respond for clients who require an adjustment.
Format your response clearly, one client per line.
"""

# ---------- Agent Wrapper ----------
def agent_runner(agent_id, model_id, profile, pdf_text):
    prompt = generate_prompt(profile, pdf_text)
    print(f"Running Agent {agent_id}...")
    try:
        response = invoke_bedrock(prompt, model_id)
    except Exception as e:
        print(f"[{agent_id}] Bedrock error: {e}")
        response = {'error': 'model access denied or failure'}
    return agent_id, response

# ---------- Main Entry Point ----------
def run_agents_on_profile(csv_path, pdf_path, row_index=0):
    df = pd.read_csv(csv_path)
    profile = df.iloc[row_index].to_dict()
    pdf_text = extract_pdf_text(pdf_path)

    agents = {
        "A1": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "A2": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "A3": "anthropic.claude-3-5-haiku-20241022-v1:0"
    }

    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(agent_runner, aid, mid, profile, pdf_text) for aid, mid in agents.items()]
        for future in futures:
            agent_id, output = future.result()
            results[agent_id] = output

    return results

if __name__ == "__main__":
    csv_path = "data_final.csv"  # Ton fichier CSV
    pdf_path = "The_different_types_of_insurance_contracts_and_details.pdf"  # À adapter si tu as un autre nom

    results = run_agents_on_profile(csv_path, pdf_path, row_index=0)

    for agent_id, output in results.items():
        print(f"\n=== {agent_id} ===\n{output}")