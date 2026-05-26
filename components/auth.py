import streamlit as st
from utils.supabase_client import get_client


def is_authenticated() -> bool:
    return st.session_state.get("user") is not None


def get_current_user() -> dict:
    return st.session_state.get("user", {})


def require_auth():
    if not is_authenticated():
        st.warning("Please log in to access this page.")
        st.stop()


def logout():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("access_token", None)


def render_login():
    st.markdown(
        """
        <style>
        .login-box { max-width: 400px; margin: 10vh auto; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.title("⚔️ GuildOS")
    st.subheader("Admin Login")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Please fill in all fields.")
            return

        try:
            supabase = get_client()
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            user = response.user
            if user:
                st.session_state["user"] = {
                    "id": user.id,
                    "email": user.email,
                    "role": user.user_metadata.get("role", "admin"),
                }
                st.session_state["access_token"] = response.session.access_token
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Login failed. Please check your credentials.")
        except Exception as e:
            st.error(f"Login error: {e}")
