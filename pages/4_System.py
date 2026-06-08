import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from utils.supabase_client import get_client

render_sidebar()

st.title("🔧 System Health")
st.caption("สถานะ AI agents และ platform connections")

supabase = get_client()

# ── AI Agent Status ───────────────────────────────────────────────────────────
st.subheader("AI Agents")

col1, col2, col3 = st.columns(3)
col1.metric("🛡️ AI Moderator",     "Active", "95% accuracy")
col2.metric("🎮 Smart Matchmaker",  "Active", "NLP enabled")
col3.metric("🧬 Profiling Engine",  "Active", "Skill Card ready")

st.divider()

# ── Moderation stats ──────────────────────────────────────────────────────────
st.subheader("Moderation Stats (All Communities)")

try:
    all_logs = supabase.table("moderation_logs") \
        .select("action_taken, label, requires_review") \
        .execute()

    if all_logs.data:
        df = pd.DataFrame(all_logs.data)

        c1, c2, c3, c4 = st.columns(4)
        total    = len(df)
        removed  = len(df[df["action_taken"] == "remove"])
        warned   = len(df[df["action_taken"].isin(["warn", "mute"])])
        pending  = len(df[df["requires_review"] == True])
        c1.metric("Total Moderated", total)
        c2.metric("Removed",         removed)
        c3.metric("Warned / Muted",  warned)
        c4.metric("Needs Review",    pending)

        st.markdown("**Label Breakdown**")
        cat = df["label"].value_counts().reset_index()
        cat.columns = ["Label", "Count"]
        st.bar_chart(cat.set_index("Label"))

        st.markdown("**Action Breakdown**")
        act = df["action_taken"].value_counts().reset_index()
        act.columns = ["Action", "Count"]
        st.bar_chart(act.set_index("Action"))
    else:
        st.info("ยังไม่มีข้อมูล moderation")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")

st.divider()

# ── Match stats ───────────────────────────────────────────────────────────────
st.subheader("Matchmaking Stats")

try:
    mx = supabase.table("matches").select("status, game, match_score").execute()
    mr = supabase.table("match_ratings").select("rating").execute()

    if mx.data:
        df_mx = pd.DataFrame(mx.data)
        total_mx  = len(df_mx)
        accepted  = len(df_mx[df_mx["status"] == "accepted"]) if "status" in df_mx.columns else 0
        rate      = (accepted / total_mx * 100) if total_mx > 0 else 0
        avg_score = df_mx["match_score"].mean() if "match_score" in df_mx.columns else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Matches",  total_mx)
        c2.metric("Accepted",       accepted)
        c3.metric("Accept Rate",    f"{rate:.0f}%")
        c4.metric("Avg Match Score", f"{avg_score:.2f}")
    else:
        st.info("ยังไม่มีข้อมูล matchmaking")

    if mr.data:
        df_mr = pd.DataFrame(mr.data)
        avg_rating = df_mr["rating"].mean()
        st.metric("Average Match Rating ⭐", f"{avg_rating:.1f} / 5.0")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")

st.divider()

# ── Platform connections ──────────────────────────────────────────────────────
st.subheader("Platform Connections")

try:
    result = supabase.table("communities") \
        .select("name, platform, is_onboarded, is_active, subscription_tier") \
        .execute()

    if result.data:
        df_c = pd.DataFrame(result.data)
        df_c["status"]  = df_c["is_onboarded"].apply(lambda x: "🟢 Active" if x else "🟡 Pending")
        df_c["active"]  = df_c["is_active"].apply(lambda x: "🟢 Yes" if x else "🔴 No")

        st.dataframe(
            df_c[["name", "platform", "subscription_tier", "status", "active"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name":              st.column_config.TextColumn("Community"),
                "platform":          st.column_config.TextColumn("Platform"),
                "subscription_tier": st.column_config.TextColumn("Plan"),
                "status":            st.column_config.TextColumn("Onboarded"),
                "active":            st.column_config.TextColumn("Active"),
            },
        )
    else:
        st.info("ยังไม่มี community")
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")

st.divider()

# ── Infrastructure ────────────────────────────────────────────────────────────
st.subheader("Infrastructure")

col_a, col_b = st.columns(2)
try:
    supabase.table("communities").select("id").limit(1).execute()
    col_a.metric("Supabase DB", "🟢 Connected")
except Exception:
    col_a.metric("Supabase DB", "🔴 Error")

col_b.metric("Streamlit Cloud", "🟢 Running")
