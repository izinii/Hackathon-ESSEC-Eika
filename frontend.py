import streamlit as st
import pandas as pd
import sqlite3
import time
import json
from init_db import import_database
from backend import run_frontend


# Paths
AUTH_DB = "./users.db"

# --- Initialize session state ---
def init_session():
    defaults = {
        "logged_in": False,
        "user_info": None,
        "notification_log": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# --- SQLite function ---
def get_conn():
    return sqlite3.connect(AUTH_DB, check_same_thread=False)

# --- Login function ---
def login_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "username": row[1],
            "role": row[3],
            "data": json.loads(row[4]) if row[4] else {}
        }
    return None



# --- Login Page ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>AI Insurance Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Secure login to access your dashboard</p>", unsafe_allow_html=True)
    st.markdown("---")

    with st.form("login_form", clear_on_submit=False):
        st.subheader("Login")
        username = st.text_input("Username", placeholder="e.g. advisor or user1000")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            user = login_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_info = user
                st.success("Login successful!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

    st.stop()



# --- Logged In Views ---
if st.session_state.logged_in:
    user = st.session_state.user_info

    # Sidebar display
    username_display = user.get("username", user.get("user_id", ""))
    st.sidebar.markdown(f"**Logged in as:** {username_display}")
    st.sidebar.markdown(f"**Role:** {user['role']}")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()

    # === CLIENT DASHBOARD ===
    if user["role"] == "client":
        st.title("Client Dashboard")

        try:
            client_id = int(user["user_id"])
        except ValueError:
            st.error("Invalid client ID.")
            st.stop()

        df = import_database("SELECT * FROM clients_database order by client_id;")
        df["client_id"] = df["client_id"].astype(int) 

        filtered = df[df["client_id"] == client_id]

        if filtered.empty:
            st.error(f"Aucun client trouvé avec l'ID {client_id}")
            st.stop()

        client_data = filtered.iloc[0].to_dict()


        st.markdown("### Update your information")
        st.caption("Keep your personal and lifestyle information up to date.")

        st.session_state.pending_changes = []
        updated = False

        # Field configuration
        editable_fields = {
            "Primary_Transportation_Mode": ["Car", "Biking", "Walking", "Public Transit"],
            "Has_Kids": [True, False],
            "Employment_Status": ["Employed", "Unemployed", "Student", "Retired"],
            "Homeownership_Status": ["Owner", "Renter", "Living with family"],
            "Type_of_Housing": ["House", "Apartment", "Other"],
            "Has_Car": [True, False],
            "Location": None,
            "Recent_Life_Event": ["Moved", "Got Married", "Had a Child", "None"],
            "Recent_Life_Event_Date": "date",
            "Annual_Income": "number",
            "Health_History": None
        }

        field_labels = {
            "Primary_Transportation_Mode": "Primary Mode of Transportation",
            "Has_Kids": "Do you have kids?",
            "Employment_Status": "Employment Status",
            "Homeownership_Status": "Homeownership",
            "Type_of_Housing": "Type of Housing",
            "Has_Car": "Do you own a car?",
            "Location": "Your Location",
            "Recent_Life_Event": "Recent Life Event",
            "Recent_Life_Event_Date": "Date of Life Event",
            "Annual_Income": "Annual Income (USD)",
            "Health_History": "Health History Summary"
        }


        # UX: Logical field grouping
        with st.expander("Housing & Transportation"):
            for field in ["Homeownership_Status", "Type_of_Housing", "Has_Car", "Primary_Transportation_Mode"]:
                current_value = client_data.get(field, "")
                label = field_labels.get(field, field)
                new_value = st.selectbox(label, editable_fields[field], index=editable_fields[field].index(current_value) if current_value in editable_fields[field] else 0, key=field)
                if new_value != current_value:
                    df.loc[df["client_id"] == client_id, field] = new_value
                    st.session_state.pending_changes.append(f'ClientID:{client_id} | "{field}" changed from "{current_value}" to "{new_value}"')
                    updated = True

        with st.expander("Personal Information"):
            for field in ["Has_Kids", "Employment_Status", "Location"]:
                current_value = client_data.get(field, "")
                label = field_labels.get(field, field)
                options = editable_fields[field]
                new_value = st.selectbox(label, options, index=options.index(current_value) if current_value in options else 0, key=field) if options else st.text_input(label, value=str(current_value), key=field)
                if new_value != current_value:
                    df.loc[df["client_id"] == client_id, field] = new_value
                    st.session_state.pending_changes.append(f'ClientID:{client_id} | "{field}" changed from "{current_value}" to "{new_value}"')
                    updated = True

        with st.expander("Income & Life Events"):
            for field in ["Annual_Income", "Recent_Life_Event", "Recent_Life_Event_Date"]:
                current_value = client_data.get(field, "")
                label = field_labels.get(field, field)
                field_type = editable_fields[field]

                if field_type == "number":
                    try:
                        new_value = st.number_input(label, value=float(current_value), key=field)
                    except:
                        new_value = st.number_input(label, value=0.0, key=field)
                elif field_type == "date":
                    new_value = st.date_input(label, pd.to_datetime(current_value) if current_value else pd.Timestamp.now(), key=field)
                    new_value = new_value.strftime("%Y-%m-%d")
                else:
                    new_value = st.selectbox(label, field_type, index=field_type.index(current_value) if current_value in field_type else 0, key=field)

                if new_value != current_value:
                    df.loc[df["client_id"] == client_id, field] = new_value
                    st.session_state.pending_changes.append(f'ClientID:{client_id} | "{field}" changed from "{current_value}" to "{new_value}"')
                    updated = True

        with st.expander("Health"):
            field = "Health_History"
            label = field_labels.get(field, field)
            current_value = client_data.get(field, "")
            new_value = st.text_area(label, value=str(current_value), key=field)
            if new_value != current_value:
                df.loc[df["client_id"] == client_id, field] = new_value
                st.session_state.pending_changes.append(f'ClientID:{client_id} | "{field}" updated.')
                updated = True

        if updated and st.button("Save Changes"):
            st.session_state.notification_log.extend(st.session_state.pending_changes)
            st.session_state.pending_changes = []
            st.success("Your profile has been updated.")
            st.rerun()



    # === ADVISOR DASHBOARD ===
    elif user["role"] == "admin":

        # --- INTERFACE ADMIN ---
        st.title("Advisor Dashboard")
        st.markdown("### AI Recommendation")

        col1, col2 = st.columns([1, 9])
        with col1:
            if st.button("💡"):
                st.session_state["run_agents_for"] = True
        with col2:
            st.markdown("Click the lightbulb to generate personalized AI recommendations.")

        if st.session_state.get("run_agents_for", False):
            run_frontend()