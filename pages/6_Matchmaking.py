import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from utils.supabase_client import get_client

render_sidebar()

st.title("🎮 Matchmaking")
st.caption("ดูและจัดการ matches ทุก community")

supabase = get_client()

try:
    comm_result = supabase.table("communities").select("id, name").execute()
    communities = {c["id"]: c["name"] for c in (comm_result.data or [])}
    community_options = ["all"] + list(communities.values())
except Exception:
    communities = {}
    community_options = ["all"]

# ── KPIs ──────────────────────────────────────────────────────────────────────
try:
    mx_all = supabase.table("matches") \
        .select("status, game, community_id, match_score, requested_at") \
        .execute()
    mx_data = mx_all.data or []
except Exception as e:
    st.warning(f"โหลด matches ไม่ได้: {e}")
    mx_data = []

try:
    ratings_r = supabase.table("match_ratings").select("rating").execute()
    ratings   = ratings_r.data or []
except Exception:
    ratings = []

c1, c2, c3, c4 = st.columns(4)
if mx_data:
    df_all   = pd.DataFrame(mx_data)
    total    = len(df_all)
    accepted = len(df_all[df_all["status"] == "accepted"]) if "status" in df_all.columns else 0
    pending  = len(df_all[df_all["status"] == "pending"])  if "status" in df_all.columns else 0
    avg_score = df_all["match_score"].mean() if "match_score" in df_all.columns else 0
    c1.metric("Total Matches",   total)
    c2.metric("Pending",         pending)
    c3.metric("Accepted",        accepted)
    c4.metric("Avg Match Score", f"{avg_score:.2f}")
else:
    c1.metric("Total Matches", 0)

if ratings:
    avg_rating = pd.DataFrame(ratings)["rating"].mean()
    st.metric("Average Rating ⭐", f"{avg_rating:.1f} / 5.0")

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns(3)
game_filter   = f1.selectbox("Game",      ["all", "ROV", "MLBB", "Valorant", "PUBG Mobile", "LoL"])
status_filter = f2.selectbox("Status",    ["all", "pending", "accepted", "rejected", "expired"])
comm_filter   = f3.selectbox("Community", community_options)

# ── Matches table ─────────────────────────────────────────────────────────────
st.subheader("Matches")

try:
    result = supabase.table("matches") \
        .select("id, community_id, game, status, match_score, game_score, time_score, role_score, style_score, requested_at, responded_at") \
        .order("requested_at", desc=True) \
        .limit(200) \
        .execute()
    matches = result.data or []
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")
    matches = []

if not matches:
    st.info("ยังไม่มี matches")
else:
    df = pd.DataFrame(matches)
    df["community_name"] = df["community_id"].map(communities).fillna("Unknown")

    if game_filter != "all" and "game" in df.columns:
        df = df[df["game"] == game_filter]
    if status_filter != "all" and "status" in df.columns:
        df = df[df["status"] == status_filter]
    if comm_filter != "all":
        df = df[df["community_name"] == comm_filter]

    st.caption(f"แสดง {len(df)} matches")

    display_cols = ["game", "community_name", "status", "match_score", "game_score", "time_score", "role_score", "requested_at"]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "game":           st.column_config.TextColumn("เกม"),
            "community_name": st.column_config.TextColumn("Community"),
            "status":         st.column_config.TextColumn("สถานะ"),
            "match_score":    st.column_config.ProgressColumn("Match Score", min_value=0, max_value=1, format="%.2f"),
            "game_score":     st.column_config.NumberColumn("Game", format="%.2f"),
            "time_score":     st.column_config.NumberColumn("Time", format="%.2f"),
            "role_score":     st.column_config.NumberColumn("Role", format="%.2f"),
            "requested_at":   st.column_config.DatetimeColumn("เวลา"),
        },
    )

st.divider()

# ── Game popularity chart ─────────────────────────────────────────────────────
st.subheader("📈 Game Popularity")
if mx_data:
    df_pop = pd.DataFrame(mx_data)
    if "game" in df_pop.columns:
        game_counts = df_pop["game"].value_counts().reset_index()
        game_counts.columns = ["Game", "Matches"]
        st.bar_chart(game_counts.set_index("Game"))

st.divider()

# ── Match ratings breakdown ───────────────────────────────────────────────────
st.subheader("⭐ Rating Distribution")
if ratings:
    df_r = pd.DataFrame(ratings)
    rating_counts = df_r["rating"].value_counts().sort_index().reset_index()
    rating_counts.columns = ["Rating", "Count"]
    rating_counts["Rating"] = rating_counts["Rating"].apply(lambda x: f"{'⭐'*x} ({x})")
    st.bar_chart(rating_counts.set_index("Rating"))
else:
    st.info("ยังไม่มี ratings")
