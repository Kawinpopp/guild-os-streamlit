import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from utils.supabase_client import get_client

render_sidebar()

st.title("📊 Data Insights")
st.caption("Cross-community analytics — สำหรับขายให้แบรนด์และค่ายเกม")

supabase = get_client()

col1, col2 = st.columns(2)
days = col1.selectbox("ช่วงเวลา", [7, 14, 30], format_func=lambda x: f"{x} วันล่าสุด")
game_filter = col2.selectbox("Game", ["all", "ROV", "MLBB", "Valorant", "PUBG Mobile", "LoL"])

since = (pd.Timestamp.now() - pd.Timedelta(days=days)).isoformat()
date_range = pd.date_range(end=pd.Timestamp.now().normalize(), periods=days)

def to_chart(s: pd.Series) -> pd.DataFrame:
    return s.reindex(date_range, fill_value=0).rename_axis("Date").reset_index(name="Count")

def daily_count(table: str, date_col: str = "created_at", filters: dict = {}) -> pd.Series:
    try:
        q = supabase.table(table).select(date_col).gte(date_col, since)
        for k, v in filters.items():
            q = q.eq(k, v)
        r = q.execute()
        if not r.data:
            return pd.Series(dtype=int)
        df = pd.DataFrame(r.data)
        df[date_col] = pd.to_datetime(df[date_col]).dt.normalize()
        return df.groupby(date_col).size()
    except Exception:
        return pd.Series(dtype=int)

# ── Section 1: Platform breakdown ─────────────────────────────────────────────
st.subheader("🏰 Platform Breakdown")
try:
    result = supabase.table("communities").select("platform, total_members").execute()
    if result.data:
        df_plat = pd.DataFrame(result.data)
        gb = df_plat.groupby("platform").agg(
            communities=("platform", "count"),
            total_members=("total_members", "sum")
        ).reset_index()
        st.dataframe(gb, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูล")
except Exception as e:
    st.warning(str(e))

st.divider()

# ── Section 2: Game popularity from matches ────────────────────────────────────
st.subheader("🎮 Game Popularity (จาก Matches)")
try:
    q = supabase.table("matches").select("game").gte("requested_at", since)
    r = q.execute()
    if r.data:
        df_game = pd.DataFrame(r.data)
        if game_filter != "all":
            df_game = df_game[df_game["game"] == game_filter]
        game_counts = df_game["game"].value_counts().reset_index()
        game_counts.columns = ["Game", "Matches"]
        st.bar_chart(game_counts.set_index("Game"))
    else:
        st.info("ยังไม่มีข้อมูล")
except Exception as e:
    st.warning(str(e))

st.divider()

# ── Section 3: Member growth trend ───────────────────────────────────────────
st.subheader("📈 Growth Trend")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**สมาชิกใหม่รายวัน** (community_members)")
    st.bar_chart(to_chart(daily_count("community_members", "joined_at")).set_index("Date"))
with col_b:
    st.markdown("**Spam ที่ถูกลบรายวัน** (moderation_logs)")
    st.bar_chart(to_chart(daily_count("moderation_logs", filters={"action_taken": "remove"})).set_index("Date"))

st.divider()

# ── Section 4: Skill card distribution ────────────────────────────────────────
st.subheader("🧬 Skill Card Distribution")
st.caption("ข้อมูลจาก skill_cards — ใช้สำหรับ Data Insight Package ขายให้แบรนด์")
try:
    result = supabase.table("skill_cards").select("game, role, play_style, goal, rank").execute()
    if result.data:
        df_sk = pd.DataFrame(result.data)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("**Top Games**")
            if "game" in df_sk.columns:
                game_c = df_sk["game"].value_counts().head(10).reset_index()
                game_c.columns = ["Game", "Count"]
                st.bar_chart(game_c.set_index("Game"))
        with col_p2:
            st.markdown("**Play Style Distribution**")
            if "play_style" in df_sk.columns:
                style_c = df_sk["play_style"].value_counts().reset_index()
                style_c.columns = ["Style", "Count"]
                st.bar_chart(style_c.set_index("Style"))

        col_p3, col_p4 = st.columns(2)
        with col_p3:
            st.markdown("**Role Distribution**")
            if "role" in df_sk.columns:
                role_c = df_sk["role"].value_counts().head(10).reset_index()
                role_c.columns = ["Role", "Count"]
                st.bar_chart(role_c.set_index("Role"))
        with col_p4:
            st.markdown("**Goal Distribution**")
            if "goal" in df_sk.columns:
                goal_c = df_sk["goal"].value_counts().reset_index()
                goal_c.columns = ["Goal", "Count"]
                st.bar_chart(goal_c.set_index("Goal"))
    else:
        st.info("ยังไม่มีข้อมูล skill cards")
except Exception as e:
    st.warning(str(e))

st.divider()

# ── Section 5: Data Insight Package export ────────────────────────────────────
st.subheader("📦 Export Data Insight Package")
st.caption("สรุปข้อมูลสำหรับส่งให้แบรนด์ — anonymized ทั้งหมด")

if st.button("Generate Report", use_container_width=True):
    try:
        sk_r   = supabase.table("skill_cards").select("game, role, play_style, goal, rank").execute()
        mx_r   = supabase.table("matches").select("game, match_score").execute()
        comm_r = supabase.table("communities").select("platform, total_members").execute()
        mem_r  = supabase.table("community_members").select("id", count="exact").execute()

        sk_df  = pd.DataFrame(sk_r.data or [])
        mx_df  = pd.DataFrame(mx_r.data or [])

        report = {
            "total_members":     mem_r.count or 0,
            "total_communities": len(comm_r.data or []),
            "top_games":         sk_df["game"].value_counts().head(5).to_dict() if not sk_df.empty and "game" in sk_df else {},
            "top_roles":         sk_df["role"].value_counts().head(5).to_dict() if not sk_df.empty and "role" in sk_df else {},
            "top_play_styles":   sk_df["play_style"].value_counts().head(5).to_dict() if not sk_df.empty and "play_style" in sk_df else {},
            "avg_match_score":   round(mx_df["match_score"].mean(), 3) if not mx_df.empty and "match_score" in mx_df else 0,
        }
        st.json(report)
        st.success("Report พร้อมแล้ว — สามารถ copy ไปใช้ได้เลย")
    except Exception as e:
        st.error(f"Generate ไม่ได้: {e}")
