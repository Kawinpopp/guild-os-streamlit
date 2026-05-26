import streamlit as st
import pandas as pd
from components.auth import render_login, is_authenticated, get_current_user, logout
from utils.supabase_client import get_client

st.set_page_config(
    page_title="GuildOS Internal",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}
[data-testid="stToolbar"] {display: none;}
</style>
""", unsafe_allow_html=True)

if not is_authenticated():
    render_login()
    st.stop()

user = get_current_user()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### ⚔️ GuildOS Internal")
st.sidebar.caption(f"Staff: {user.get('email', '')}")
st.sidebar.divider()
st.sidebar.page_link("app.py",                       label="Global Overview",  icon="🌐")
st.sidebar.page_link("pages/1_Communities.py",        label="Communities",      icon="🏰")
st.sidebar.page_link("pages/2_Data_Insights.py",      label="Data Insights",    icon="📊")
st.sidebar.page_link("pages/3_AI_Lab.py",             label="AI Lab",           icon="🤖")
st.sidebar.page_link("pages/4_System.py",             label="System Health",    icon="🔧")
st.sidebar.divider()
if st.sidebar.button("Logout", use_container_width=True):
    logout()
    st.rerun()

# ── Global Overview ───────────────────────────────────────────────────────────
st.title("🌐 Global Overview")
st.caption("ภาพรวมทุก community บน GuildOS")

supabase = get_client()

# ── KPIs across ALL communities ───────────────────────────────────────────────
try:
    communities = supabase.table("communities").select("id", count="exact").execute()
    community_count = communities.count or 0
except Exception:
    community_count = 0

try:
    members = supabase.table("members").select("id", count="exact").execute()
    member_count = members.count or 0
except Exception:
    member_count = 0

try:
    today = pd.Timestamp.now().normalize().isoformat()
    spam = supabase.table("flagged_posts") \
        .select("id", count="exact") \
        .eq("status", "removed") \
        .gte("created_at", today).execute()
    spam_count = spam.count or 0
except Exception:
    spam_count = 0

try:
    matches = supabase.table("teams").select("id", count="exact").execute()
    team_count = matches.count or 0
except Exception:
    team_count = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Communities", community_count)
col2.metric("Total Members", f"{member_count:,}")
col3.metric("Spam Removed Today", spam_count)
col4.metric("Teams Formed (All time)", team_count)

st.divider()

# ── Community health table ────────────────────────────────────────────────────
st.subheader("Community Health")

try:
    result = supabase.table("communities") \
        .select("name, platform, member_count, onboarded, created_at") \
        .order("member_count", desc=True) \
        .execute()

    if result.data:
        df = pd.DataFrame(result.data)
        df["onboarded"] = df["onboarded"].apply(lambda x: "🟢 Active" if x else "🟡 Pending")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "name":         st.column_config.TextColumn("Community"),
                "platform":     st.column_config.TextColumn("Platform"),
                "member_count": st.column_config.NumberColumn("Members"),
                "onboarded":    st.column_config.TextColumn("Status"),
                "created_at":   st.column_config.DatetimeColumn("Joined"),
            },
        )
    else:
        st.info("ยังไม่มี community")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")

st.divider()

# ── Revenue estimate ──────────────────────────────────────────────────────────
st.subheader("Revenue Estimate (MRR)")
try:
    plans = supabase.table("communities") \
        .select("settings") \
        .execute()

    starter = pro = enterprise = 0
    for row in (plans.data or []):
        plan = (row.get("settings") or {}).get("plan", "Starter")
        if plan == "Starter":    starter += 1
        elif plan == "Pro":      pro += 1
        elif plan == "Enterprise": enterprise += 1

    mrr = (starter * 490) + (pro * 1490) + (enterprise * 2990)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Starter",    starter,    f"฿{starter * 490:,}/mo")
    c2.metric("Pro",        pro,        f"฿{pro * 1490:,}/mo")
    c3.metric("Enterprise", enterprise, f"฿{enterprise * 2990:,}/mo")
    c4.metric("Total MRR",  "",         f"฿{mrr:,}")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")
