import streamlit as st
from components.auth import get_current_user, logout, require_auth
from utils.supabase_client import get_client

# Matches Next.js dashboard layout.tsx nav order exactly
NAV = [
    ("app.py",                   "🌐", "Overview"),
    ("pages/7_Moderation.py",    "🛡️", "Moderation"),
    ("pages/6_Matchmaking.py",   "🎮", "Matchmaking"),
    ("pages/5_Members.py",       "👥", "Members"),
    ("pages/2_Data_Insights.py", "📊", "Insights"),
    ("pages/8_Settings.py",      "⚙️", "Settings"),
]

GLOBAL_CSS = """
<style>
/* Hide Streamlit auto-generated page nav (replaced by our custom links below) */
[data-testid="stSidebarNav"] { display: none !important; }

/* Hide toolbar / deploy button / footer — but NOT the sidebar toggle */
#MainMenu, footer, .stDeployButton { display: none !important; }

/* Always show the sidebar expand/collapse button */
[data-testid="stSidebarCollapsedControl"] { display: flex !important; visibility: visible !important; }

/* Metric card background */
[data-testid="stMetric"] {
    background: #1A1A2E;
    border: 1px solid #2D2D44;
    border-radius: 10px;
    padding: 1rem;
}

/* Expander border */
[data-testid="stExpander"] {
    border: 1px solid #2D2D44;
    border-radius: 8px;
}
</style>
"""


def render_sidebar():
    """Call at the top of every page. Handles auth + renders sidebar nav."""
    require_auth()
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    user = get_current_user()

    # ── Branding ──────────────────────────────────────────────────────────────
    st.sidebar.markdown("## ⚔️ GuildOS")
    st.sidebar.caption("Internal Dashboard")
    st.sidebar.divider()

    # ── Navigation links (st.sidebar.page_link renders BELOW stSidebarNav) ───
    for path, icon, label in NAV:
        st.sidebar.page_link(path, label=label, icon=icon)

    st.sidebar.divider()

    # ── Community info ────────────────────────────────────────────────────────
    try:
        supabase = get_client()
        comm_r = supabase.table("communities") \
            .select("name, total_members").limit(1).execute()
        if comm_r.data:
            c = comm_r.data[0]
            st.sidebar.markdown(f"**🏰 {c['name']}**")
            st.sidebar.caption(f"👥 {c.get('total_members', 0):,} members")
    except Exception:
        pass

    st.sidebar.caption(f"📧 {user.get('email', '')}")
    st.sidebar.divider()

    if st.sidebar.button("ออกจากระบบ", use_container_width=True):
        logout()
        st.rerun()
