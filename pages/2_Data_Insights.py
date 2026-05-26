import streamlit as st
import pandas as pd
from components.auth import require_auth
from utils.supabase_client import get_client

require_auth()

st.title("📊 Data Insights")
st.caption("Cross-community analytics — สำหรับขายให้แบรนด์และค่ายเกม")

supabase = get_client()

# ── Date range selector ───────────────────────────────────────────────────────
col1, col2 = st.columns(2)
days = col1.selectbox("ช่วงเวลา", [7, 14, 30], format_func=lambda x: f"{x} วันล่าสุด")
game_filter = col2.selectbox("Game", ["all", "ROV", "MLBB", "Valorant", "PUBG Mobile", "LoL"])

since = (pd.Timestamp.now() - pd.Timedelta(days=days)).isoformat()

# ── Helper ────────────────────────────────────────────────────────────────────
def daily(table: str, filters: dict = {}) -> pd.Series:
    try:
        q = supabase.table(table).select("created_at").gte("created_at", since)
        for k, v in filters.items():
            q = q.eq(k, v)
        r = q.execute()
        if not r.data:
            return pd.Series(dtype=int)
        df = pd.DataFrame(r.data)
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.normalize()
        return df.groupby("created_at").size()
    except Exception:
        return pd.Series(dtype=int)

date_range = pd.date_range(end=pd.Timestamp.now().normalize(), periods=days)

def to_chart(s: pd.Series) -> pd.DataFrame:
    return s.reindex(date_range, fill_value=0).rename_axis("Date").reset_index(name="Count")

# ── Section 1: Platform breakdown ─────────────────────────────────────────────
st.subheader("🏰 Platform Breakdown")
try:
    result = supabase.table("communities").select("platform, member_count").execute()
    if result.data:
        df_plat = pd.DataFrame(result.data)
        gb = df_plat.groupby("platform").agg(
            communities=("platform", "count"),
            total_members=("member_count", "sum")
        ).reset_index()
        st.dataframe(gb, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูล")
except Exception as e:
    st.warning(str(e))

st.divider()

# ── Section 2: Game popularity ────────────────────────────────────────────────
st.subheader("🎮 Game Popularity (จาก Match Requests)")
try:
    q = supabase.table("match_requests").select("game").gte("created_at", since)
    r = q.execute()
    if r.data:
        df_game = pd.DataFrame(r.data)
        game_counts = df_game["game"].value_counts().reset_index()
        game_counts.columns = ["Game", "Requests"]
        st.bar_chart(game_counts.set_index("Game"))
    else:
        st.info("ยังไม่มีข้อมูล")
except Exception as e:
    st.warning(str(e))

st.divider()

# ── Section 3: Member growth trend ───────────────────────────────────────────
st.subheader("📈 Member Growth Trend")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**สมาชิกใหม่รายวัน**")
    st.bar_chart(to_chart(daily("members")).set_index("Date"))
with col_b:
    st.markdown("**Spam ที่ถูกลบรายวัน**")
    st.bar_chart(to_chart(daily("flagged_posts", {"status": "removed"})).set_index("Date"))

st.divider()

# ── Section 4: Persona distribution ──────────────────────────────────────────
st.subheader("🧬 Persona Distribution")
st.caption("ข้อมูลนี้ใช้สำหรับ Data Insight Package ขายให้แบรนด์")
try:
    result = supabase.table("members").select("persona_tag, engagement_score").execute()
    if result.data:
        df_persona = pd.DataFrame(result.data)
        persona_counts = df_persona["persona_tag"].value_counts().head(10).reset_index()
        persona_counts.columns = ["Persona", "Count"]

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("**Top 10 Personas**")
            st.bar_chart(persona_counts.set_index("Persona"))
        with col_p2:
            st.markdown("**Engagement Score Distribution**")
            bins = pd.cut(df_persona["engagement_score"], bins=[0, 40, 60, 80, 100],
                          labels=["🥉 Bronze", "🥈 Silver", "🥇 Gold", "💎 Diamond"])
            tier_counts = bins.value_counts().reset_index()
            tier_counts.columns = ["Tier", "Count"]
            st.bar_chart(tier_counts.set_index("Tier"))
    else:
        st.info("ยังไม่มีข้อมูล personas")
except Exception as e:
    st.warning(str(e))

st.divider()

# ── Section 5: Data Insight Package export ────────────────────────────────────
st.subheader("📦 Export Data Insight Package")
st.caption("สรุปข้อมูลสำหรับส่งให้แบรนด์ — anonymized ทั้งหมด")

if st.button("Generate Report", use_container_width=True):
    try:
        members_r  = supabase.table("members").select("persona_tag, engagement_score").execute()
        matches_r  = supabase.table("match_requests").select("game").execute()
        community_r = supabase.table("communities").select("platform, member_count").execute()

        report = {
            "total_members":    len(members_r.data or []),
            "total_communities": len(community_r.data or []),
            "top_games":        pd.DataFrame(matches_r.data or [])["game"].value_counts().head(5).to_dict()
                                if matches_r.data else {},
            "top_personas":     pd.DataFrame(members_r.data or [])["persona_tag"].value_counts().head(5).to_dict()
                                if members_r.data else {},
            "avg_engagement":   round(pd.DataFrame(members_r.data or [{"engagement_score": 0}])
                                      ["engagement_score"].mean(), 1),
        }
        st.json(report)
        st.success("Report พร้อมแล้ว — สามารถ copy ไปใช้ได้เลย")
    except Exception as e:
        st.error(f"Generate ไม่ได้: {e}")
