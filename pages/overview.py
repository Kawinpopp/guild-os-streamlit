import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from components.auth import get_current_user

supabase = get_client()
user = get_current_user()


def get_community():
    uid = user.get("id")
    if not uid:
        return None
    try:
        r = supabase.table("communities").select(
            "id, name, platform, total_members"
        ).eq("admin_auth_id", uid).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


community = get_community()
cid = community["id"] if community else None
today_str = pd.Timestamp.now(tz="UTC").normalize().isoformat()

st.title("Overview")
st.caption("สถานะชุมชนของคุณแบบเรียลไทม์")

# ── Stats cards ───────────────────────────────────────────────────────────────
m_count = p_count = s_count = mx_count = 0
if cid:
    try:
        m_count = supabase.table("community_members").select("id", count="exact").eq("community_id", cid).eq("is_active", True).execute().count or 0
    except Exception:
        pass
    try:
        p_count = supabase.table("posts").select("id", count="exact").eq("community_id", cid).gte("created_at", today_str).execute().count or 0
    except Exception:
        pass
    try:
        s_count = supabase.table("moderation_logs").select("id", count="exact").eq("community_id", cid).eq("action_taken", "remove").gte("created_at", today_str).execute().count or 0
    except Exception:
        pass
    try:
        mx_count = supabase.table("matches").select("id", count="exact").eq("community_id", cid).gte("requested_at", today_str).execute().count or 0
    except Exception:
        pass

c1, c2, c3, c4 = st.columns(4)
c1.metric("Active Members", f"{m_count:,}")
c2.metric("Posts Today", p_count)
c3.metric("Spam Blocked Today", s_count)
c4.metric("Matches Today", mx_count)

st.divider()

# ── Live Moderation Feed ──────────────────────────────────────────────────────
head_col, live_col = st.columns([5, 1])
head_col.subheader("Live Moderation Feed")
live_col.markdown(
    "<div style='text-align:right; margin-top:8px'>"
    "<span style='color:#16c784'>● </span>"
    "<span style='color:#888; font-size:.85em'>Realtime</span>"
    "</div>",
    unsafe_allow_html=True,
)

ACTION_EMOJI = {"remove": "🛡", "warn": "⚠️", "mute": "🔇", "pass": "✅"}

try:
    q = supabase.table("moderation_logs").select(
        "id, label, action_taken, confidence_score, created_at, users(display_name)"
    ).order("created_at", desc=True).limit(20)
    if cid:
        q = q.eq("community_id", cid)
    feed = q.execute().data or []

    if not feed:
        st.info("ยังไม่มีกิจกรรม")
    else:
        for f in feed:
            action = f.get("action_taken", "")
            label = f.get("label", "")
            score = f.get("confidence_score", 0) or 0
            users_data = f.get("users") or {}
            name = users_data.get("display_name", "unknown") if isinstance(users_data, dict) else "unknown"
            ts = f.get("created_at", "")
            try:
                ts_display = pd.Timestamp(ts).strftime("%H:%M") if ts else ""
            except Exception:
                ts_display = ts[11:16] if len(ts) > 15 else ts
            emoji = ACTION_EMOJI.get(action, "🤖")
            st.markdown(
                f"{emoji} AI **{action}** — {label} ({score:.0%}) from {name} "
                f"<span style='color:#888; font-size:.85em'>· {ts_display}</span>",
                unsafe_allow_html=True,
            )
except Exception as e:
    st.warning(f"โหลดไม่ได้: {e}")
