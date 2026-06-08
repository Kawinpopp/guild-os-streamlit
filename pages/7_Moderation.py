import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from utils.supabase_client import get_client

render_sidebar()

st.title("🛡️ Moderation")
st.caption("ตรวจสอบและจัดการเนื้อหาที่ถูก flag บน GuildOS")

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
    all_logs = supabase.table("moderation_logs") \
        .select("action_taken, label, requires_review") \
        .execute()
    logs_data = all_logs.data or []
except Exception as e:
    st.warning(f"โหลดข้อมูลไม่ได้: {e}")
    logs_data = []

c1, c2, c3, c4 = st.columns(4)
if logs_data:
    df_kpi   = pd.DataFrame(logs_data)
    total    = len(df_kpi)
    needs_rv = len(df_kpi[df_kpi["requires_review"] == True])
    removed  = len(df_kpi[df_kpi["action_taken"] == "remove"])
    passed   = len(df_kpi[df_kpi["action_taken"] == "pass"])
    c1.metric("Total Moderated",  total)
    c2.metric("🟡 Needs Review",  needs_rv)
    c3.metric("🔴 Removed",       removed)
    c4.metric("🟢 Passed",        passed)
else:
    c1.metric("Total Moderated", 0)

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns(3)
review_filter = f1.selectbox("Queue",     ["Needs Review", "All", "Reviewed"])
label_filter  = f2.selectbox("Label",     ["all", "spam", "toxic", "sell_id", "normal"])
comm_filter   = f3.selectbox("Community", community_options)

# ── Fetch moderation logs with post content ────────────────────────────────────
try:
    q = supabase.table("moderation_logs") \
        .select("id, community_id, post_id, user_id, label, confidence_score, action_taken, requires_review, created_at") \
        .order("created_at", desc=True) \
        .limit(200)

    if review_filter == "Needs Review":
        q = q.eq("requires_review", True)
    if label_filter != "all":
        q = q.eq("label", label_filter)

    result = q.execute()
    logs = result.data or []
except Exception as e:
    st.error(f"โหลดข้อมูลไม่ได้: {e}")
    logs = []

# Fetch existing human_reviews to know which logs are already reviewed
try:
    hr_r = supabase.table("human_reviews").select("moderation_log_id, decision").execute()
    reviewed_map = {h["moderation_log_id"]: h["decision"] for h in (hr_r.data or [])}
except Exception:
    reviewed_map = {}

# Fetch post content
post_ids = list({log["post_id"] for log in logs if log.get("post_id")})
post_map: dict = {}
if post_ids:
    try:
        posts_r = supabase.table("posts") \
            .select("id, content_preview, is_blocked") \
            .in_("id", post_ids[:50]) \
            .execute()
        post_map = {p["id"]: p for p in (posts_r.data or [])}
    except Exception:
        pass

if comm_filter != "all":
    logs = [l for l in logs if communities.get(l.get("community_id")) == comm_filter]
if review_filter == "Reviewed":
    logs = [l for l in logs if l["id"] in reviewed_map]

if not logs:
    st.info("ไม่มีรายการในหมวดนี้")
    st.stop()

st.caption(f"แสดง {len(logs)} รายการ")
st.divider()

# ── Moderation queue ──────────────────────────────────────────────────────────
LABEL_COLOR  = {"spam": "🔴", "toxic": "🟠", "sell_id": "🟡", "normal": "🟢"}
ACTION_COLOR = {"remove": "🔴", "warn": "🟠", "mute": "🟡", "pass": "🟢"}

for log in logs:
    log_id     = log.get("id")
    label      = log.get("label", "?")
    action     = log.get("action_taken", "?")
    confidence = log.get("confidence_score", 0) or 0
    community  = communities.get(log.get("community_id"), "—")
    post       = post_map.get(log.get("post_id"), {})
    content    = post.get("content_preview", "— (ไม่มี content) —")
    is_blocked = post.get("is_blocked", False)
    decision   = reviewed_map.get(log_id)

    label_icon  = LABEL_COLOR.get(label, "⚪")
    action_icon = ACTION_COLOR.get(action, "⚪")
    reviewed_badge = f"  ✅ Reviewed: {decision}" if decision else ""

    with st.expander(f"{label_icon} [{label.upper()}]  {action_icon} {action}  ·  {community}  ·  {confidence:.0%}{reviewed_badge}"):
        st.markdown("**เนื้อหา:**")
        st.code(content or "—", language=None)

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Label",      label)
        mc2.metric("Action",     action)
        mc3.metric("Confidence", f"{confidence:.0%}")

        if decision:
            st.success(f"Human review: **{decision}**")
        elif log.get("requires_review"):
            bc1, bc2 = st.columns(2)
            if bc1.button("✅ Confirm AI decision", key=f"confirm_{log_id}", use_container_width=True):
                try:
                    supabase.table("human_reviews").insert({
                        "moderation_log_id": log_id,
                        "decision": "confirm",
                    }).execute()
                    st.success("Confirmed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

            if bc2.button("🔄 Override (let through)", key=f"override_{log_id}", use_container_width=True):
                try:
                    supabase.table("human_reviews").insert({
                        "moderation_log_id": log_id,
                        "decision": "override",
                    }).execute()
                    if post.get("id"):
                        supabase.table("posts").update({"is_blocked": False}).eq("id", post["id"]).execute()
                    st.success("Overridden — post unblocked!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

st.divider()

# ── Label breakdown chart ─────────────────────────────────────────────────────
st.subheader("📊 Label Breakdown")
if logs_data:
    df_chart = pd.DataFrame(logs_data)
    if "label" in df_chart.columns:
        label_counts = df_chart["label"].value_counts().reset_index()
        label_counts.columns = ["Label", "Count"]
        st.bar_chart(label_counts.set_index("Label"))
