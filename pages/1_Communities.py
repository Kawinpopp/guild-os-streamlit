import streamlit as st
import pandas as pd
from components.auth import require_auth
from utils.supabase_client import get_client

require_auth()

st.title("🏰 Communities")
st.caption("รายละเอียดทุก community บน GuildOS")

supabase = get_client()

# ── Fetch all communities ─────────────────────────────────────────────────────
try:
    result = supabase.table("communities") \
        .select("id, name, platform, member_count, group_url, webhook_url, onboarded, settings, created_at") \
        .order("member_count", desc=True) \
        .execute()
    communities = result.data or []
except Exception as e:
    st.error(f"โหลดข้อมูลไม่ได้: {e}")
    communities = []

if not communities:
    st.info("ยังไม่มี community")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
platform_filter = col1.selectbox("Platform", ["all", "Facebook", "Discord", "LINE"])
status_filter   = col2.selectbox("Status",   ["all", "Active", "Pending"])

df = pd.DataFrame(communities)
if platform_filter != "all":
    df = df[df["platform"] == platform_filter]
if status_filter == "Active":
    df = df[df["onboarded"] == True]
elif status_filter == "Pending":
    df = df[df["onboarded"] != True]

st.caption(f"แสดง {len(df)} จาก {len(communities)} communities")
st.divider()

# ── Community cards ───────────────────────────────────────────────────────────
PLATFORM_ICON = {"Facebook": "📘", "Discord": "💬", "LINE": "💚"}

for _, row in df.iterrows():
    icon   = PLATFORM_ICON.get(row.get("platform", ""), "🏰")
    status = "🟢 Active" if row.get("onboarded") else "🟡 Pending"
    plan   = (row.get("settings") or {}).get("plan", "Starter")

    with st.expander(f"{icon} {row.get('name', 'Unnamed')}  ·  {status}  ·  {plan}"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Members",  f"{row.get('member_count', 0):,}")
        c2.metric("Platform", row.get("platform", "—"))
        c3.metric("Plan",     plan)

        if row.get("group_url"):
            st.markdown(f"**Group URL:** {row['group_url']}")
        if row.get("webhook_url"):
            st.code(row["webhook_url"], language=None)
            st.caption("Webhook URL")

        # Per-community stats
        cid = row.get("id")
        if cid:
            try:
                m = supabase.table("members") \
                    .select("id", count="exact") \
                    .eq("community_id", cid).execute()
                fp = supabase.table("flagged_posts") \
                    .select("id", count="exact") \
                    .eq("community_id", cid) \
                    .eq("status", "pending").execute()
                mr = supabase.table("match_requests") \
                    .select("id", count="exact") \
                    .eq("community_id", cid).execute()

                s1, s2, s3 = st.columns(3)
                s1.metric("Members (DB)",      m.count  or 0)
                s2.metric("Pending Moderation", fp.count or 0)
                s3.metric("Match Requests",    mr.count or 0)
            except Exception:
                pass
