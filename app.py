import streamlit as st
from components.auth import is_authenticated, _render_auth_page, get_current_user, logout
from utils.supabase_client import get_client

st.set_page_config(
    page_title="GuildOS",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not is_authenticated():
    _render_auth_page()
    st.stop()

overview_page       = st.Page("pages/overview.py",       title="Overview",      icon="🌐", default=True)
moderation_page     = st.Page("pages/7_Moderation.py",   title="Moderation",    icon="🛡️")
matchmaking_page    = st.Page("pages/6_Matchmaking.py",  title="Matchmaking",   icon="⚔️")
members_page        = st.Page("pages/5_Members.py",      title="Members",       icon="👥")
insights_page       = st.Page("pages/2_Data_Insights.py", title="Insights",     icon="📊")
member_portal_page  = st.Page("pages/member_portal.py",  title="Member Portal", icon="📡")
settings_page       = st.Page("pages/8_Settings.py",     title="Settings",      icon="⚙️")

pg = st.navigation(
    [
        overview_page,
        moderation_page,
        matchmaking_page,
        members_page,
        insights_page,
        member_portal_page,
        settings_page,
    ],
    position="sidebar",
)

st.markdown("""
<style>
#MainMenu, footer, .stDeployButton { display: none !important; }
[data-testid="stMetric"] {
    background: #1A1A2E;
    border: 1px solid #2D2D44;
    border-radius: 10px;
    padding: 1rem;
}
[data-testid="stExpander"] { border: 1px solid #2D2D44; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.divider()
    try:
        supabase = get_client()
        user = get_current_user()
        uid = user.get("id")
        comm_r = supabase.table("communities").select("name, platform, total_members").eq("admin_auth_id", uid).limit(1).execute()
        if comm_r.data:
            c = comm_r.data[0]
            st.markdown(
                f"<span style='color:#16c784'>●</span> **{c['name']}**",
                unsafe_allow_html=True,
            )
            st.caption(f"{(c.get('platform') or '').capitalize()} · {c.get('total_members', 0):,} members")
    except Exception:
        pass
    user = get_current_user()
    st.caption(f"📧 {user.get('email', '')}")
    st.divider()
    if st.button("ออกจากระบบ", use_container_width=True):
        logout()
        st.rerun()

pg.run()
