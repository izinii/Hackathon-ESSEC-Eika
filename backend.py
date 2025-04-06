from ai_agents import final_run
import pandas as pd
import pandas as pd
import boto3
import streamlit as st

# === CONFIGURATION ===
DB_PATH = "users.db" # SQLite database to generate

client = boto3.client('redshift-data', region_name='us-west-2')
database = 'dev'
workgroup_name = 'redshift-wg-hackathon'



def orchestrate_agents(client_id: int, csv_path: str, pdf_path: str) -> dict:
    """
    Orchestrates the full AI agent pipeline for a single client.

    Args:
        client_id (int): Client ID to match from CSV
        csv_path (str): Path to client CSV
        pdf_path (str): Path to offers PDF

    Returns:
        dict: Agent outputs (A1, A2, B, C, etc.)
    """
    df = pd.read_csv(csv_path)

    # Match client row index
    match = df[df["Client_ID"] == client_id]
    if match.empty:
        raise ValueError(f"Client ID {client_id} not found in dataset.")
    row_index = match.index[0]

    return final_run()



def run_frontend():
    """
    Runs the IA agents (A1 to D) and displays the results in Streamlit.
    """
    st.session_state["run_agents_for"] = False  # Reset
    with st.spinner("Running AI agents..."):
        try:
            results = final_run()

            if results is None:
                st.error("The final_run() function did not return any results.")
                return

            st.success("AI agents have completed the recommendation process.")

            st.subheader("🧠 Agent A1 (Claude)")
            st.code(results.get("A1 (Claude)", "No result"), language="markdown")

            st.subheader("🤖 Agent A2 (Mistral)")
            st.code(results.get("A2 (Mistral)", "No result"), language="markdown")

            st.subheader("🧩 Agent B - Consensus Recommendation")
            st.code(results.get("Consensus", "No result"), language="markdown")

            st.subheader("🕵️ Agent C - Reverse Validator")
            st.code(results.get("Agent C", "No result"), language="markdown")

            st.subheader("📧 Agent D - Summurization & Email Notification")
            st.code(results.get("Email", "No result"), language="markdown")

            st.success("📨 Email successfully sent via MailHog.")

        except Exception as e:
            st.error(f"An error occurred while running the AI agents: {e}")