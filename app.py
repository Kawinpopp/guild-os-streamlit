import streamlit as st
from components.auth import is_authenticated, _render_auth_page, get_current_user, logout
from utils.supabase_client import get_client
from utils.community import get_community

st.set_page_config(
    page_title="GuildOS",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not is_authenticated():
    _render_auth_page()
    st.stop()

# ── Onboarding gate ────────────────────────────────────────────────────────────
# Skip if we just completed onboarding this session
if not st.session_state.get("_onboarding_done"):
    try:
        _supabase = get_client()
        _uid = get_current_user().get("id")
        if _uid:
            import time as _time
            _cache_key = f"_comm_cache_{_uid}"
            _cache_ts_key = f"_comm_cache_{_uid}_ts"
            _now = _time.time()
            # Cache community record for 60 s to avoid a DB hit on every page
            if _cache_key not in st.session_state or (_now - st.session_state.get(_cache_ts_key, 0)) > 60:
                _comm = _supabase.table("communities").select("id, is_onboarded").eq("admin_auth_id", _uid).limit(1).execute()
                st.session_state[_cache_key] = _comm.data[0] if _comm.data else None
                st.session_state[_cache_ts_key] = _now
            _comm_row = st.session_state[_cache_key]
            if _comm_row and not _comm_row.get("is_onboarded", True):
                from components.onboarding import render_onboarding
                render_onboarding()
                st.stop()
    except Exception:
        pass

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
    _sidebar_comm = get_community()
    if _sidebar_comm:
        st.markdown(
            f"<span style='color:#16c784'>●</span> **{_sidebar_comm['name']}**",
            unsafe_allow_html=True,
        )
        st.caption(
            f"{(_sidebar_comm.get('platform') or '').capitalize()} · "
            f"{_sidebar_comm.get('total_members', 0):,} members"
        )
    user = get_current_user()
    st.caption(f"📧 {user.get('email', '')}")
    st.divider()
    if st.button("ออกจากระบบ", use_container_width=True):
        logout()
        st.rerun()

pg.run()
