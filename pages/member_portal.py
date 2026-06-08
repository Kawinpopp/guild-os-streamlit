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
            "id, name, platform, total_members, platform_group_id"
        ).eq("admin_auth_id", uid).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


community = get_community()
cid = community["id"] if community else None

st.title("Member Portal")
st.caption("ลิงก์สาธารณะสำหรับสมาชิกชุมชน — แชร์ให้สมาชิกดูทีมและ leaderboard ได้เลย")

# ── Shareable link ─────────────────────────────────────────────────────────────
st.subheader("🔗 ลิงก์ Portal สาธารณะ")
st.caption("แชร์ลิงก์นี้ให้สมาชิก — พวกเขาสามารถดูผลการจับคู่และ leaderboard ได้โดยไม่ต้องล็อกอิน")

platform_group_id = community.get("platform_group_id", "") if community else ""
portal_url = f"https://guildos.app/portal/{platform_group_id}" if platform_group_id else "—"

url_col, copy_col = st.columns([5, 1])
url_col.code(portal_url, language=None)
if copy_col.button("📋 Copy", use_container_width=True):
    st.toast("คัดลอกแล้ว!", icon="✅")

st.divider()

# ── Fetch data ────────────────────────────────────────────────────────────────
matches = []
top_members = []

if cid:
    try:
        q = supabase.table("matches").select(
            "id, game, match_score, status, requested_at, "
            "requester:users!matches_requester_id_fkey(display_name), "
            "matched_user:users!matches_matched_user_id_fkey(display_name)"
        ).eq("community_id", cid).order("requested_at", desc=True).limit(10)
        matches = q.execute().data or []
    except Exception:
        try:
            q2 = supabase.table("matches").select(
                "id, game, match_score, status, requested_at, requester_id, matched_user_id"
            ).eq("community_id", cid).order("requested_at", desc=True).limit(10)
            raw = q2.execute().data or []
            user_ids = list({m.get("requester_id") for m in raw if m.get("requester_id")} |
                           {m.get("matched_user_id") for m in raw if m.get("matched_user_id")})
            user_map = {}
            if user_ids:
                ur = supabase.table("users").select("id, display_name").in_("id", user_ids[:100]).execute()
                user_map = {u["id"]: u["display_name"] for u in (ur.data or [])}
            for m in raw:
                m["requester"] = {"display_name": user_map.get(m.get("requester_id"), "—")}
                m["matched_user"] = {"display_name": user_map.get(m.get("matched_user_id"), "—")}
            matches = raw
        except Exception:
            pass

    try:
        og_r = supabase.table("community_members").select(
            "role, joined_at, users(display_name, platform_type, last_active_at)"
        ).eq("community_id", cid).eq("is_active", True).order("joined_at", desc=False).limit(10).execute()
        top_members = og_r.data or []
    except Exception:
        pass

# ── Two-column layout ─────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

STATUS_COLOR = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴", "expired": "⚫"}

with col_left:
    count_badge = len(matches)
    st.subheader(f"⚔️ การจับคู่ล่าสุด  `{count_badge}`")

    if not matches:
        st.info("ยังไม่มีการจับคู่")
    else:
        for m in matches:
            game = m.get("game", "—")
            status = m.get("status", "—")
            score = m.get("match_score", 0) or 0
            requester_name = (m.get("requester") or {}).get("display_name", "—")
            matched_name = (m.get("matched_user") or {}).get("display_name", "—")
            ts = m.get("requested_at", "")
            try:
                ts_display = pd.Timestamp(ts).strftime("%d %b %H:%M") if ts else "—"
            except Exception:
                ts_display = ts[:16]

            with st.container(border=True):
                st.markdown(
                    f"**{game}**  {STATUS_COLOR.get(status, '⚪')} {status}"
                )
                st.caption(f"{requester_name} vs {matched_name}")
                sc1, sc2 = st.columns(2)
                sc1.caption(ts_display)
                sc2.markdown(f"<div style='text-align:right; font-weight:bold'>{score:.0%}</div>", unsafe_allow_html=True)

with col_right:
    st.subheader("🏆 OG Members  `สมาชิกเก่าสุด 10 คน`")

    if not top_members:
        st.info("ยังไม่มีสมาชิก")
    else:
        for i, m in enumerate(top_members):
            u = m.get("users") or {}
            name = u.get("display_name", "—")
            role = m.get("role", "—")
            platform = u.get("platform_type", "—")
            joined = m.get("joined_at", "")
            try:
                joined = pd.Timestamp(joined).strftime("%d %b") if joined else "—"
            except Exception:
                pass
            rank_icon = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i + 1}."

            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                c1.markdown(f"<div style='font-size:1.5rem;text-align:center'>{rank_icon}</div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{name}**")
                    st.caption(f"{role} · {platform} · joined {joined}")

st.divider()

# ── Community info ─────────────────────────────────────────────────────────────
st.subheader("🏰 ข้อมูลชุมชน")
if community:
    i1, i2, i3 = st.columns(3)
    i1.metric("ชื่อชุมชน", community.get("name", "—"))
    i2.metric("แพลตฟอร์ม", (community.get("platform") or "—").capitalize())
    i3.metric("จำนวนสมาชิก", f"{community.get('total_members', 0):,}")
else:
    st.info("ไม่พบข้อมูลชุมชน")
