import streamlit as st
import pandas as pd
from utils.supabase_client import get_client

st.title("🏰 Communities")
st.caption("รายละเอียดทุก community บน GuildOS")

supabase = get_client()

try:
    result = supabase.table("communities") \
        .select("id, name, platform, total_members, is_onboarded, subscription_tier, matchmaker_config, created_at") \
        .order("total_members", desc=True) \
        .execute()
    communities = result.data or []
except Exception as e:
    st.error(f"โหลดข้อมูลไม่ได้: {e}")
    communities = []

if not communities:
    st.info("ยังไม่มี community — ต้องล็อกอินด้วย account ที่มี admin_auth_id ตรงกับ community ใน DB")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
platform_filter = col1.selectbox("Platform", ["all", "facebook", "discord", "line"])
status_filter   = col2.selectbox("Status",   ["all", "Active", "Pending"])

df = pd.DataFrame(communities)
if platform_filter != "all":
    df = df[df["platform"].str.lower() == platform_filter]
if status_filter == "Active":
    df = df[df["is_onboarded"] == True]
elif status_filter == "Pending":
    df = df[df["is_onboarded"] != True]

st.caption(f"แสดง {len(df)} จาก {len(communities)} communities")
st.divider()

# ── Community cards ───────────────────────────────────────────────────────────
PLATFORM_ICON = {"facebook": "📘", "discord": "💬", "line": "💚"}

for _, row in df.iterrows():
    platform = (row.get("platform") or "").lower()
    icon   = PLATFORM_ICON.get(platform, "🏰")
    status = "🟢 Active" if row.get("is_onboarded") else "🟡 Pending"
    tier   = row.get("subscription_tier") or "free"

    with st.expander(f"{icon} {row.get('name', 'Unnamed')}  ·  {status}  ·  {tier.capitalize()}"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Members",  f"{row.get('total_members', 0):,}")
        c2.metric("Platform", row.get("platform", "—"))
        c3.metric("Plan",     tier.capitalize())

        # matchmaker config
        mc = row.get("matchmaker_config") or {}
        if mc:
            st.caption(f"Matchmaker time window: {mc.get('time_window', 60)} นาที")

        # Per-community stats
        cid = row.get("id")
        if cid:
            try:
                m  = supabase.table("community_members") \
                    .select("id", count="exact") \
                    .eq("community_id", cid).execute()
                ml = supabase.table("moderation_logs") \
                    .select("id", count="exact") \
                    .eq("community_id", cid) \
                    .eq("requires_review", True).execute()
                mx = supabase.table("matches") \
                    .select("id", count="exact") \
                    .eq("community_id", cid).execute()

                s1, s2, s3 = st.columns(3)
                s1.metric("Members (DB)",       m.count  or 0)
                s2.metric("Needs Review",        ml.count or 0)
                s3.metric("Matches",             mx.count or 0)
            except Exception:
                pass
