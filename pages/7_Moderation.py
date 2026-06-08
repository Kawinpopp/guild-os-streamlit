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
        r = supabase.table("communities").select("id, name, platform").eq("admin_auth_id", uid).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


community = get_community()
cid = community["id"] if community else None

# ── Header ────────────────────────────────────────────────────────────────────
h_col, btn_col = st.columns([5, 1])
h_col.title("AI Moderation")
h_col.caption("ตรวจจับและจัดการโพสต์ที่ไม่เหมาะสมด้วย AI")
if btn_col.button("🔄 Refresh", use_container_width=True):
    st.rerun()

# ── Fetch all logs ────────────────────────────────────────────────────────────
try:
    q = supabase.table("moderation_logs").select(
        "id, label, confidence_score, action_taken, requires_review, created_at, "
        "posts(content_preview, is_blocked), users(display_name, platform_type), "
        "human_reviews(id, decision, reviewed_at)"
    ).order("created_at", desc=True).limit(200)
    if cid:
        q = q.eq("community_id", cid)
    items = q.execute().data or []
except Exception as e:
    st.error(f"โหลดข้อมูลไม่ได้: {e}")
    items = []


def is_reviewed(item):
    reviews = item.get("human_reviews") or []
    return bool(reviews) and reviews[0].get("decision") is not None


# ── Stats cards ───────────────────────────────────────────────────────────────
pending_count = sum(1 for i in items if i.get("requires_review") and not is_reviewed(i))
reviewed_count = sum(1 for i in items if is_reviewed(i))

s1, s2, s3 = st.columns(3)
s1.metric("Needs Review", pending_count)
s2.metric("Reviewed", reviewed_count)
s3.metric("Total Flagged", len(items))

# ── Filter tabs ───────────────────────────────────────────────────────────────
if "mod_filter" not in st.session_state:
    st.session_state["mod_filter"] = "pending"

tab_labels = [
    f"Pending Review ({pending_count})" if st.session_state["mod_filter"] == "pending" else "Pending Review",
    "Reviewed",
    "All",
]
tab_keys = ["pending", "reviewed", "all"]

cols = st.columns(len(tab_keys))
for i, (col, key, label) in enumerate(zip(cols, tab_keys, tab_labels)):
    active = st.session_state["mod_filter"] == key
    if col.button(
        label,
        key=f"mod_tab_{key}",
        use_container_width=True,
        type="primary" if active else "secondary",
    ):
        st.session_state["mod_filter"] = key
        st.rerun()

filter_val = st.session_state["mod_filter"]

if filter_val == "pending":
    filtered = [i for i in items if i.get("requires_review") and not is_reviewed(i)]
elif filter_val == "reviewed":
    filtered = [i for i in items if is_reviewed(i)]
else:
    filtered = items

# ── Detail dialog ─────────────────────────────────────────────────────────────
LABEL_COLOR = {"spam": "🔴", "toxic": "🟠", "sell_id": "🟡", "normal": "🟢"}
ACTION_COLOR = {"remove": "🔴", "warn": "🟠", "mute": "🟡", "pass": "🟢"}


@st.dialog("Post Detail", width="large")
def show_detail(item):
    users_data = item.get("users") or {}
    posts_data = item.get("posts") or {}
    reviews = item.get("human_reviews") or []
    reviewed = bool(reviews) and reviews[0].get("decision") is not None

    st.markdown(f"**Author:** {users_data.get('display_name', '—')}")
    st.markdown("**Content:**")
    st.code(posts_data.get("content_preview") or "—", language=None)

    col1, col2 = st.columns(2)
    col1.markdown(f"**Platform:** {users_data.get('platform_type', '—')}")
    col2.markdown(f"**Label:** {item.get('label', '—')}")

    score = item.get("confidence_score", 0) or 0
    col3, col4 = st.columns(2)
    col3.markdown(f"**AI Score:** {score:.0%}")
    col4.markdown(f"**AI Action:** {item.get('action_taken', '—')}")

    if reviewed:
        st.success(f"Human Decision: **{reviews[0]['decision']}**")
    elif item.get("requires_review"):
        st.divider()
        bc1, bc2, bc3 = st.columns(3)
        if bc1.button("✅ Confirm AI", key=f"dlg_confirm_{item['id']}", use_container_width=True):
            try:
                supabase.table("human_reviews").insert({
                    "moderation_log_id": item["id"],
                    "decision": "confirm",
                    "reviewed_at": pd.Timestamp.now().isoformat(),
                }).execute()
                st.success("ยืนยันการดำเนินการแล้ว")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if bc2.button("🔄 Ignore", key=f"dlg_ignore_{item['id']}", use_container_width=True):
            try:
                supabase.table("human_reviews").insert({
                    "moderation_log_id": item["id"],
                    "decision": "ignore",
                    "reviewed_at": pd.Timestamp.now().isoformat(),
                }).execute()
                st.success("ข้ามแล้ว")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if bc3.button("❌ Override", key=f"dlg_override_{item['id']}", use_container_width=True):
            try:
                supabase.table("human_reviews").insert({
                    "moderation_log_id": item["id"],
                    "decision": "override",
                    "reviewed_at": pd.Timestamp.now().isoformat(),
                }).execute()
                st.success("Override แล้ว")
                st.rerun()
            except Exception as e:
                st.error(str(e))


# ── Items list ────────────────────────────────────────────────────────────────
if not filtered:
    st.info("✅ ไม่มีโพสต์ที่ต้องดำเนินการ")
    st.stop()

st.caption(f"แสดง {len(filtered)} รายการ")

for item in filtered:
    item_id = item.get("id", "")
    label = item.get("label", "?")
    action = item.get("action_taken", "?")
    score = item.get("confidence_score", 0) or 0
    users_data = item.get("users") or {}
    posts_data = item.get("posts") or {}
    reviews = item.get("human_reviews") or []
    reviewed = bool(reviews) and reviews[0].get("decision") is not None

    display_name = users_data.get("display_name", "—")
    platform_type = users_data.get("platform_type", "—")
    content_preview = posts_data.get("content_preview", "—")
    ts = item.get("created_at", "")
    try:
        ts_display = pd.Timestamp(ts).strftime("%d %b %H:%M") if ts else "—"
    except Exception:
        ts_display = ts[:16]

    l_icon = LABEL_COLOR.get(label, "⚪")
    a_icon = ACTION_COLOR.get(action, "⚪")

    with st.container(border=True):
        row1, row_score = st.columns([6, 1])
        with row1:
            badge_parts = [
                f"**{display_name}**",
                f"`{platform_type}`",
                f"{l_icon} {label}",
                f"{a_icon} AI: {action}",
            ]
            if reviewed:
                badge_parts.append(f"✅ {reviews[0]['decision']}")
            st.markdown("  ·  ".join(badge_parts))
            st.caption(f"{content_preview[:120]}{'…' if len(content_preview or '') > 120 else ''}")
            st.caption(ts_display)
        with row_score:
            score_pct = int(score * 100)
            color = "🔴" if score >= 0.85 else "🟠" if score >= 0.6 else "⚪"
            st.metric(f"{color} Score", score_pct)

        btn_cols = st.columns([1, 2, 2, 4])
        if btn_cols[0].button("👁", key=f"view_{item_id}", help="ดูเนื้อหา"):
            show_detail(item)

        if item.get("requires_review") and not reviewed:
            if btn_cols[1].button("✅ Confirm", key=f"confirm_{item_id}", use_container_width=True):
                try:
                    supabase.table("human_reviews").insert({
                        "moderation_log_id": item_id,
                        "decision": "confirm",
                        "reviewed_at": pd.Timestamp.now().isoformat(),
                    }).execute()
                    st.success("ยืนยันแล้ว")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            if btn_cols[2].button("❌ Override", key=f"override_{item_id}", use_container_width=True):
                try:
                    supabase.table("human_reviews").insert({
                        "moderation_log_id": item_id,
                        "decision": "override",
                        "reviewed_at": pd.Timestamp.now().isoformat(),
                    }).execute()
                    st.success("Override แล้ว")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
