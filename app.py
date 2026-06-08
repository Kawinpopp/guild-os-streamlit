import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from utils.supabase_client import get_client

st.set_page_config(
    page_title="GuildOS Internal",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()  # handles auth — shows login/register if not authenticated

supabase = get_client()
today = pd.Timestamp.now().normalize().isoformat()

# ── KPIs (matches Next.js: Active Members, Posts Today, Spam Blocked, Matches Today) ──
st.title("🌐 Overview")

try:
    active_members = supabase.table("community_members") \
        .select("id", count="exact").eq("is_active", True).execute()
    m_count = active_members.count or 0
except Exception:
    m_count = 0

try:
    posts_today = supabase.table("posts") \
        .select("id", count="exact").gte("created_at", today).execute()
    p_count = posts_today.count or 0
except Exception:
    p_count = 0

try:
    spam_today = supabase.table("moderation_logs") \
        .select("id", count="exact") \
        .eq("action_taken", "remove") \
        .gte("created_at", today).execute()
    s_count = spam_today.count or 0
except Exception:
    s_count = 0

try:
    matches_today = supabase.table("matches") \
        .select("id", count="exact").gte("requested_at", today).execute()
    mx_count = matches_today.count or 0
except Exception:
    mx_count = 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Active Members",    f"{m_count:,}")
c2.metric("📝 Posts Today",       p_count)
c3.metric("🚫 Spam Blocked",      s_count)
c4.metric("🎮 Matches Today",     mx_count)

st.divider()

# ── Recent moderation activity feed (matches Next.js real-time feed) ──────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("🛡️ Recent Moderation Activity")

    ACTION_ICON = {"remove": "🗑️", "warn": "⚠️", "mute": "🔇", "pass": "✅"}
    LABEL_COLOR = {"spam": "🔴", "toxic": "🟠", "sell_id": "🟡", "normal": "🟢"}

    try:
        activity = supabase.table("moderation_logs") \
            .select("label, action_taken, confidence_score, created_at, community_id") \
            .order("created_at", desc=True) \
            .limit(20).execute()

        if activity.data:
            # Fetch community names
            comm_r = supabase.table("communities").select("id, name").execute()
            comm_map = {c["id"]: c["name"] for c in (comm_r.data or [])}

            for log in activity.data:
                label      = log.get("label", "?")
                action     = log.get("action_taken", "?")
                confidence = log.get("confidence_score", 0) or 0
                comm_name  = comm_map.get(log.get("community_id"), "—")
                ts         = log.get("created_at", "")[:16].replace("T", " ")
                a_icon     = ACTION_ICON.get(action, "•")
                l_icon     = LABEL_COLOR.get(label, "⚪")

                st.markdown(
                    f"{a_icon} &nbsp; {l_icon} **{label}** — `{action}` &nbsp; "
                    f"<span style='color:#888;font-size:.85em'>{comm_name} · {ts} · {confidence:.0%}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("ยังไม่มี moderation activity")
    except Exception as e:
        st.warning(f"โหลดไม่ได้: {e}")

with col_right:
    st.subheader("🏰 Communities")

    try:
        comm_list = supabase.table("communities") \
            .select("name, platform, total_members, is_onboarded, subscription_tier") \
            .order("total_members", desc=True).execute()

        if comm_list.data:
            PLAT_ICON = {"facebook": "📘", "discord": "💬", "line": "💚"}
            for c in comm_list.data:
                platform = (c.get("platform") or "").lower()
                icon     = PLAT_ICON.get(platform, "🏰")
                status   = "🟢" if c.get("is_onboarded") else "🟡"
                tier     = (c.get("subscription_tier") or "free").capitalize()
                members  = c.get("total_members", 0) or 0

                st.markdown(
                    f"{icon} **{c['name']}** {status} &nbsp;"
                    f"<span style='color:#888;font-size:.85em'>{tier} · {members:,} members</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("ยังไม่มี community")
    except Exception as e:
        st.warning(f"โหลดไม่ได้: {e}")

st.divider()

# ── Match score breakdown ─────────────────────────────────────────────────────
st.subheader("🎮 Recent Matches")
try:
    mx_r = supabase.table("matches") \
        .select("game, match_score, game_score, time_score, role_score, style_score, status, requested_at") \
        .order("requested_at", desc=True).limit(10).execute()

    if mx_r.data:
        df_mx = pd.DataFrame(mx_r.data)
        df_mx["requested_at"] = pd.to_datetime(df_mx["requested_at"]).dt.strftime("%Y-%m-%d %H:%M")
        STATUS_ICON = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴", "expired": "⚫"}
        df_mx["สถานะ"] = df_mx["status"].map(lambda s: f"{STATUS_ICON.get(s,'⚪')} {s}")

        st.dataframe(
            df_mx[["game", "สถานะ", "match_score", "game_score", "time_score", "role_score", "style_score", "requested_at"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "game":        st.column_config.TextColumn("เกม"),
                "สถานะ":       st.column_config.TextColumn("สถานะ"),
                "match_score": st.column_config.ProgressColumn("Overall", min_value=0, max_value=1, format="%.2f"),
                "game_score":  st.column_config.NumberColumn("Game",  format="%.2f"),
                "time_score":  st.column_config.NumberColumn("Time",  format="%.2f"),
                "role_score":  st.column_config.NumberColumn("Role",  format="%.2f"),
                "style_score": st.column_config.NumberColumn("Style", format="%.2f"),
                "requested_at":st.column_config.TextColumn("เวลา"),
            },
        )
    else:
        st.info("ยังไม่มี matches")
except Exception as e:
    st.warning(f"โหลดไม่ได้: {e}")
