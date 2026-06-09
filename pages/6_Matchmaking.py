import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from utils.ai_helpers import run_community_matchmaker
from components.auth import get_current_user

supabase = get_client()
user = get_current_user()


def get_community():
    uid = user.get("id")
    if not uid:
        return None
    try:
        r = supabase.table("communities").select("id, name").eq("admin_auth_id", uid).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


community = get_community()
cid = community["id"] if community else None

# ── Header ────────────────────────────────────────────────────────────────────
h_col, run_col, btn_col = st.columns([4, 1, 1])
h_col.title("Smart Matchmaker")
h_col.caption("ผลการจับคู่จาก AI Matchmaker — score คำนวณจาก game / time / role / style")
if btn_col.button("🔄 Refresh", use_container_width=True):
    st.rerun()
if run_col.button("⚔️ Run", type="primary", use_container_width=True, help="รัน AI Matchmaker สำหรับสมาชิกทุกคนในชุมชน"):
    if not cid:
        st.warning("ไม่พบ community")
    else:
        with st.spinner("กำลังรัน AI Matchmaker..."):
            matched, errors = run_community_matchmaker(cid, supabase)
        if matched > 0:
            st.success(f"สร้างการจับคู่ใหม่ {matched} คู่ สำเร็จ")
        elif errors:
            st.warning("รัน Matchmaker แล้ว แต่ไม่มีคู่ใหม่ (อาจมี pending อยู่แล้ว หรือ Skill Cards ไม่เพียงพอ)")
        else:
            st.info("ไม่มีสมาชิกที่มี Skill Card เพียงพอสำหรับการจับคู่")
        st.rerun()

# ── Fetch matches ─────────────────────────────────────────────────────────────
try:
    q = supabase.table("matches").select(
        "id, game, match_score, game_score, time_score, role_score, style_score, "
        "status, requested_at, responded_at, "
        "requester:users!matches_requester_id_fkey(display_name), "
        "matched_user:users!matches_matched_user_id_fkey(display_name)"
    ).order("requested_at", desc=True).limit(100)
    if cid:
        q = q.eq("community_id", cid)
    matches = q.execute().data or []
except Exception:
    # Fallback: fetch without foreign key aliases
    try:
        q = supabase.table("matches").select(
            "id, game, match_score, game_score, time_score, role_score, style_score, "
            "status, requested_at, responded_at, requester_id, matched_user_id"
        ).order("requested_at", desc=True).limit(100)
        if cid:
            q = q.eq("community_id", cid)
        raw = q.execute().data or []

        # Fetch user names separately
        user_ids = list({m.get("requester_id") for m in raw if m.get("requester_id")} |
                        {m.get("matched_user_id") for m in raw if m.get("matched_user_id")})
        user_map = {}
        if user_ids:
            try:
                ur = supabase.table("users").select("id, display_name").in_("id", user_ids[:100]).execute()
                user_map = {u["id"]: u["display_name"] for u in (ur.data or [])}
            except Exception:
                pass

        for m in raw:
            m["requester"] = {"display_name": user_map.get(m.get("requester_id"), "—")}
            m["matched_user"] = {"display_name": user_map.get(m.get("matched_user_id"), "—")}
        matches = raw
    except Exception as e:
        st.error(f"โหลดข้อมูลไม่ได้: {e}")
        matches = []

# ── Stats ─────────────────────────────────────────────────────────────────────
pending_count = sum(1 for m in matches if m.get("status") == "pending")
accepted_count = sum(1 for m in matches if m.get("status") == "accepted")
rejected_count = sum(1 for m in matches if m.get("status") == "rejected")
avg_score = (
    sum(m.get("match_score", 0) or 0 for m in matches) / len(matches)
    if matches else 0
)

s1, s2, s3, s4 = st.columns(4)
s1.metric("Pending", pending_count)
s2.metric("Accepted", accepted_count)
s3.metric("Rejected", rejected_count)
s4.metric("Avg Score", f"{avg_score:.2f}" if matches else "—")

# ── Filter tabs ───────────────────────────────────────────────────────────────
if "mx_filter" not in st.session_state:
    st.session_state["mx_filter"] = "all"

filter_options = ["all", "pending", "accepted", "rejected"]
tab_cols = st.columns(len(filter_options))
for col, key in zip(tab_cols, filter_options):
    active = st.session_state["mx_filter"] == key
    if col.button(
        key.capitalize(),
        key=f"mx_tab_{key}",
        use_container_width=True,
        type="primary" if active else "secondary",
    ):
        st.session_state["mx_filter"] = key
        st.rerun()

filter_val = st.session_state["mx_filter"]
filtered = matches if filter_val == "all" else [m for m in matches if m.get("status") == filter_val]

STATUS_COLOR = {
    "pending": "🟡",
    "accepted": "🟢",
    "rejected": "🔴",
    "expired": "⚫",
}


# ── Detail dialog ─────────────────────────────────────────────────────────────
@st.dialog("Match Detail", width="large")
def show_match_detail(m):
    requester_name = (m.get("requester") or {}).get("display_name", "—")
    matched_name = (m.get("matched_user") or {}).get("display_name", "—")
    status = m.get("status", "—")

    # Matchup header
    mc1, mc2, mc3 = st.columns([2, 1, 2])
    mc1.metric("Requester", requester_name)
    mc2.markdown("<div style='text-align:center; margin-top:32px; font-weight:bold'>vs</div>", unsafe_allow_html=True)
    mc3.metric("Matched", matched_name)

    st.divider()

    d1, d2 = st.columns(2)
    d1.markdown(f"**Game:** {m.get('game', '—')}")
    d2.markdown(f"**Status:** {STATUS_COLOR.get(status, '⚪')} {status}")

    req_ts = m.get("requested_at", "")
    res_ts = m.get("responded_at", "")
    try:
        req_ts = pd.Timestamp(req_ts).strftime("%d/%m/%Y %H:%M") if req_ts else "—"
    except Exception:
        pass
    try:
        res_ts = pd.Timestamp(res_ts).strftime("%d/%m/%Y %H:%M") if res_ts else "—"
    except Exception:
        pass

    d3, d4 = st.columns(2)
    d3.markdown(f"**Requested:** {req_ts}")
    d4.markdown(f"**Responded:** {res_ts}")

    st.markdown("**Score Breakdown**")
    scores = [
        ("Overall Match", m.get("match_score", 0) or 0),
        ("Game (40%)", m.get("game_score", 0) or 0),
        ("Time (25%)", m.get("time_score", 0) or 0),
        ("Role (20%)", m.get("role_score", 0) or 0),
        ("Style (15%)", m.get("style_score", 0) or 0),
    ]
    for label, val in scores:
        b1, b2 = st.columns([3, 1])
        b1.progress(float(val), text=label)
        b2.markdown(f"<div style='margin-top:8px'>{val:.0%}</div>", unsafe_allow_html=True)

    if status == "pending":
        st.divider()
        a1, a2 = st.columns(2)
        if a1.button("❌ ปฏิเสธ", key=f"dlg_reject_{m['id']}", use_container_width=True):
            try:
                supabase.table("matches").update({
                    "status": "rejected",
                    "responded_at": pd.Timestamp.now().isoformat(),
                }).eq("id", m["id"]).execute()
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if a2.button("✅ รับการจับคู่", key=f"dlg_accept_{m['id']}", use_container_width=True, type="primary"):
            try:
                supabase.table("matches").update({
                    "status": "accepted",
                    "responded_at": pd.Timestamp.now().isoformat(),
                }).eq("id", m["id"]).execute()
                st.rerun()
            except Exception as e:
                st.error(str(e))


# ── Matches list ──────────────────────────────────────────────────────────────
if not filtered:
    st.info("ยังไม่มีการจับคู่")
    st.stop()

st.caption(f"แสดง {len(filtered)} matches")

for m in filtered:
    m_id = m.get("id", "")
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

    score_color = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "⚪"
    status_icon = STATUS_COLOR.get(status, "⚪")

    with st.container(border=True):
        row_main, row_score = st.columns([6, 1])
        with row_main:
            st.markdown(
                f"⚔️ **{requester_name}** vs **{matched_name}** "
                f"  `{game}`  {status_icon} {status}"
            )
            st.caption(ts_display)
        with row_score:
            st.metric(f"{score_color} Score", f"{score:.0%}")

        if st.button("👁 View Details", key=f"mx_view_{m_id}", use_container_width=True):
            show_match_detail(m)
