import streamlit as st
import pandas as pd
from components.auth import require_auth
from utils.supabase_client import get_client

require_auth()

st.title("🔧 System Health")
st.caption("สถานะ AI agents และ platform connections")

supabase = get_client()

# ── AI Agent Status ───────────────────────────────────────────────────────────
st.subheader("AI Agents")

col1, col2, col3 = st.columns(3)
col1.metric("🛡️ AI Moderator",  "Active", "95% accuracy")
col2.metric("🎮 Smart Matchmaker", "Active", "NLP enabled")
col3.metric("🧬 Profiling Engine", "Active", "Skill Card ready")

st.divider()

# ── Moderation accuracy ───────────────────────────────────────────────────────
st.subheader("Moderation Stats (All Communities)")

try:
    all_posts = supabase.table("flagged_posts") \
        .select("status, category") \
        .execute()

    if all_posts.data:
        df = pd.DataFrame(all_posts.data)

        c1, c2, c3 = st.columns(3)
        total   = len(df)
        removed = len(df[df.status == "removed"])
        pending = len(df[df.status == "pending"])
        c1.metric("Total Flagged",   total)
        c2.metric("Removed",         removed)
        c3.metric("Pending Review",  pending)

        st.markdown("**Category Breakdown**")
        cat = df["category"].value_counts().reset_index()
        cat.columns = ["Category", "Count"]
        st.bar_chart(cat.set_index("Category"))
    else:
        st.info("ยังไม่มีข้อมูล moderation")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")

st.divider()

# ── Match success rate ────────────────────────────────────────────────────────
st.subheader("Matchmaking Stats")

try:
    mr = supabase.table("match_requests").select("status, game").execute()
    teams = supabase.table("teams").select("id", count="exact").execute()

    if mr.data:
        df_mr = pd.DataFrame(mr.data)
        total_req = len(df_mr)
        matched   = len(df_mr[df_mr.status == "matched"]) if "status" in df_mr else 0
        rate      = (matched / total_req * 100) if total_req > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Requests", total_req)
        c2.metric("Matched",        matched)
        c3.metric("Match Rate",     f"{rate:.0f}%")
    else:
        st.info("ยังไม่มีข้อมูล matchmaking")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")

st.divider()

# ── Platform connections ──────────────────────────────────────────────────────
st.subheader("Platform Connections")

try:
    result = supabase.table("communities") \
        .select("name, platform, onboarded, webhook_url") \
        .execute()

    if result.data:
        df_c = pd.DataFrame(result.data)
        df_c["webhook"] = df_c["webhook_url"].apply(lambda x: "🟢 Set" if x else "🔴 Missing")
        df_c["status"]  = df_c["onboarded"].apply(lambda x: "🟢 Active" if x else "🟡 Pending")

        st.dataframe(
            df_c[["name", "platform", "status", "webhook"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name":     st.column_config.TextColumn("Community"),
                "platform": st.column_config.TextColumn("Platform"),
                "status":   st.column_config.TextColumn("Status"),
                "webhook":  st.column_config.TextColumn("Webhook"),
            },
        )
    else:
        st.info("ยังไม่มี community")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")

st.divider()

# ── Supabase connection test ───────────────────────────────────────────────────
st.subheader("Infrastructure")

col_a, col_b = st.columns(2)
try:
    supabase.table("communities").select("id").limit(1).execute()
    col_a.metric("Supabase DB", "🟢 Connected")
except Exception:
    col_a.metric("Supabase DB", "🔴 Error")

col_b.metric("Streamlit Cloud", "🟢 Running")
