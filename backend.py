from ai_agents import final_run
import pandas as pd


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



