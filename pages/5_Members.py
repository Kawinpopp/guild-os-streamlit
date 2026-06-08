import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from utils.supabase_client import get_client

render_sidebar()

st.title("👥 Members")
st.caption("จัดการสมาชิกทั้งหมดบน GuildOS")

supabase = get_client()

# Fetch communities for filter
try:
    comm_result = supabase.table("communities").select("id, name").execute()
    communities = {c["id"]: c["name"] for c in (comm_result.data or [])}
    community_options = ["all"] + list(communities.values())
except Exception:
    communities = {}
    community_options = ["all"]

# Fetch users with their skill cards via community_members
try:
    users_r = supabase.table("users") \
        .select("id, display_name, platform_type, warning_count, status, onboarding_completed, created_at") \
        .order("created_at", desc=True) \
        .execute()
    users = users_r.data or []
except Exception as e:
    st.error(f"โหลดข้อมูลไม่ได้: {e}")
    users = []

try:
    sc_r = supabase.table("skill_cards") \
        .select("user_id, community_id, game, role, play_style, goal, rank, available_time") \
        .execute()
    skill_map = {s["user_id"]: s for s in (sc_r.data or [])}
except Exception:
    skill_map = {}

try:
    cm_r = supabase.table("community_members") \
        .select("user_id, community_id, role, is_active") \
        .execute()
    cm_map: dict[str, list] = {}
    for cm in (cm_r.data or []):
        cm_map.setdefault(cm["user_id"], []).append(cm)
except Exception:
    cm_map = {}

if not users:
    st.info("ยังไม่มีสมาชิก")
    st.stop()

# Build merged dataframe
rows = []
for u in users:
    uid = u["id"]
    sc  = skill_map.get(uid, {})
    rows.append({
        "id":           uid,
        "display_name": u.get("display_name", "—"),
        "platform":     u.get("platform_type", "—"),
        "status":       u.get("status", "active"),
        "warning_count":u.get("warning_count", 0),
        "onboarded":    u.get("onboarding_completed", False),
        "game":         sc.get("game", "—"),
        "role":         sc.get("role", "—"),
        "play_style":   sc.get("play_style", "—"),
        "goal":         sc.get("goal", "—"),
        "rank":         sc.get("rank", "—"),
        "community_id": sc.get("community_id"),
        "created_at":   u.get("created_at"),
    })

df = pd.DataFrame(rows)
df["community_name"] = df["community_id"].map(communities).fillna("—")

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Members", len(df))
c2.metric("Onboarded",     len(df[df["onboarded"] == True]))
c3.metric("Warned",        len(df[df["warning_count"] > 0]))
c4.metric("Banned / Muted",len(df[df["status"].isin(["banned", "muted"])]))

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns(3)
comm_filter   = f1.selectbox("Community", community_options)
game_filter   = f2.selectbox("Game", ["all", "ROV", "MLBB", "Valorant", "PUBG Mobile", "LoL"])
status_filter = f3.selectbox("Status", ["all", "active", "warned", "muted", "banned"])

filtered = df.copy()
if comm_filter != "all":
    filtered = filtered[filtered["community_name"] == comm_filter]
if game_filter != "all":
    filtered = filtered[filtered["game"] == game_filter]
if status_filter != "all":
    filtered = filtered[filtered["status"] == status_filter]

st.caption(f"แสดง {len(filtered)} จาก {len(df)} สมาชิก")
st.divider()

# ── Member table ──────────────────────────────────────────────────────────────
display_cols = ["display_name", "community_name", "platform", "game", "role", "rank", "status", "warning_count"]
st.dataframe(
    filtered[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "display_name":   st.column_config.TextColumn("ชื่อ"),
        "community_name": st.column_config.TextColumn("Community"),
        "platform":       st.column_config.TextColumn("Platform"),
        "game":           st.column_config.TextColumn("เกม"),
        "role":           st.column_config.TextColumn("Role"),
        "rank":           st.column_config.TextColumn("Rank"),
        "status":         st.column_config.TextColumn("สถานะ"),
        "warning_count":  st.column_config.NumberColumn("Warnings"),
    },
)

st.divider()
st.subheader("รายละเอียดสมาชิก")

STATUS_ICON = {"active": "🟢", "warned": "🟡", "muted": "🟠", "banned": "🔴"}

for _, row in filtered.iterrows():
    icon = STATUS_ICON.get(row.get("status", "active"), "⚪")
    name = row.get("display_name", "—")
    game = row.get("game", "—")

    with st.expander(f"{icon} {name}  ·  {game}  ·  {row.get('rank','—')}"):
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Platform",     row.get("platform", "—"))
        mc2.metric("Status",       row.get("status", "—"))
        mc3.metric("Warnings",     row.get("warning_count", 0))

        mc4, mc5 = st.columns(2)
        mc4.metric("Play Style",   row.get("play_style", "—"))
        mc5.metric("Goal",         row.get("goal", "—"))

        mc6, mc7 = st.columns(2)
        mc6.metric("Role",         row.get("role", "—"))
        mc7.metric("Community",    row.get("community_name", "—"))
