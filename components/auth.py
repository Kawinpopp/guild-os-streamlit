import streamlit as st
from utils.supabase_client import get_client


def is_authenticated() -> bool:
    if st.session_state.get("user"):
        return True
    # Fallback: recover from Supabase client's stored session
    try:
        session = get_client().auth.get_session()
        if session and session.user:
            st.session_state["user"] = {
                "id":    session.user.id,
                "email": session.user.email,
                "role":  session.user.user_metadata.get("role", "admin"),
            }
            st.session_state["access_token"] = session.access_token
            return True
    except Exception:
        pass
    return False


def get_current_user() -> dict:
    return st.session_state.get("user", {})


def require_auth():
    """Show login/register UI inline and stop — no redirect."""
    if not is_authenticated():
        _render_auth_page()
        st.stop()


def logout():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    for key in ("user", "access_token", "_supabase"):
        st.session_state.pop(key, None)


# ── Internal: full-screen auth page ──────────────────────────────────────────

def _render_auth_page():
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    .block-container { max-width: 460px !important; margin: 8vh auto !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## ⚔️ GuildOS")
    st.markdown("#### Internal Dashboard")
    st.divider()

    tab_login, tab_register = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])

    with tab_login:
        _login_form()

    with tab_register:
        _register_form()


def render_login():
    """Alias kept for app.py compatibility."""
    _render_auth_page()


# ── Login form ────────────────────────────────────────────────────────────────

def _login_form():
    slot = st.empty()          # clears the form immediately after success

    with slot.form("login_form"):
        email    = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit   = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)

    if submit:
        if not email or not password:
            st.error("กรุณากรอก Email และ Password")
            return
        with st.spinner("กำลังเข้าสู่ระบบ..."):
            try:
                supabase = get_client()
                res  = supabase.auth.sign_in_with_password({"email": email, "password": password})
                user = res.user
                if user:
                    st.session_state["user"] = {
                        "id":    user.id,
                        "email": user.email,
                        "role":  user.user_metadata.get("role", "admin"),
                    }
                    st.session_state["access_token"] = res.session.access_token
                    slot.empty()   # clear the form before rerun → no ghost
                    st.rerun()
                else:
                    st.error("เข้าสู่ระบบไม่สำเร็จ กรุณาตรวจสอบ Email / Password")
            except Exception as e:
                st.error(f"Error: {e}")


# ── Register form ─────────────────────────────────────────────────────────────

def _register_form():
    slot = st.empty()

    with slot.form("register_form"):
        st.markdown("**ข้อมูลบัญชี**")
        reg_email   = st.text_input("Email",            key="reg_email")
        reg_pw      = st.text_input("Password",         key="reg_pw",  type="password",
                                    help="อย่างน้อย 6 ตัวอักษร")
        reg_pw2     = st.text_input("Confirm Password", key="reg_pw2", type="password")

        st.divider()
        st.markdown("**ข้อมูล Community**")
        comm_name     = st.text_input("ชื่อ Community")
        comm_platform = st.selectbox("Platform", ["facebook", "discord", "line"])
        comm_group_id = st.text_input("Platform Group ID",
                                      help="Discord server ID / Facebook group ID / LINE group ID")
        submit = st.form_submit_button("สมัครสมาชิก", use_container_width=True)

    if submit:
        if not reg_email or not reg_pw or not comm_name or not comm_group_id:
            st.error("กรุณากรอกข้อมูลให้ครบ")
            return
        if reg_pw != reg_pw2:
            st.error("Password ไม่ตรงกัน")
            return
        if len(reg_pw) < 6:
            st.error("Password ต้องมีอย่างน้อย 6 ตัวอักษร")
            return

        with st.spinner("กำลังสร้างบัญชี..."):
            try:
                supabase = get_client()

                # 1. Create auth user
                res  = supabase.auth.sign_up({"email": reg_email, "password": reg_pw})
                user = res.user
                if not user:
                    st.error("สมัครสมาชิกไม่สำเร็จ")
                    return

                # 2. Sign in to get a valid JWT for RLS
                login_res = supabase.auth.sign_in_with_password(
                    {"email": reg_email, "password": reg_pw}
                )
                token = login_res.session.access_token
                st.session_state["user"] = {
                    "id":    user.id,
                    "email": user.email,
                    "role":  "admin",
                }
                st.session_state["access_token"] = token
                supabase.postgrest.auth(token)

                # 3. Create community owned by this user
                supabase.table("communities").insert({
                    "name":              comm_name,
                    "platform":          comm_platform,
                    "platform_group_id": comm_group_id,
                    "admin_auth_id":     user.id,
                    "subscription_tier": "free",
                    "is_onboarded":      False,
                    "is_active":         True,
                }).execute()

                slot.empty()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
