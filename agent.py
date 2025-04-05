import boto3
import json

session = boto3.Session(profile_name="default", region_name="us-west-2")

# --------------------------------------------------------------------------------------------


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

