import streamlit as st
from supabase import create_client, Client


def get_client() -> Client:
    # Store client in session_state (per-session, not global cache)
    # so the auth session inside the client persists across page navigations
    if "_supabase" not in st.session_state:
        st.session_state["_supabase"] = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_ANON_KEY"],
        )
    client: Client = st.session_state["_supabase"]

    # Attach user JWT so RLS policies resolve correctly
    token = st.session_state.get("access_token")
    if token:
        client.postgrest.auth(token)

    return client
