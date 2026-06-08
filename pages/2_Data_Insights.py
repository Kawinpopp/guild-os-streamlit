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
        r = supabase.table("communities").select("id, name").eq("admin_auth_id", uid).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


community = get_community()
cid = community["id"] if community else None

st.title("Insights")
st.caption("ภาพรวมสถิติชุมชน 7 วันล่าสุด")

# ── Build 7-day date range ────────────────────────────────────────────────────
days = []
for i in range(7):
    d = pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=6 - i)
    days.append(d)

since_str = days[0].isoformat()

# ── Fetch totals & 7-day data ─────────────────────────────────────────────────
total_members = posts_flagged = posts_removed = total_matches = 0

day_posts: dict = {d: 0 for d in days}
day_removed: dict = {d: 0 for d in days}
day_matches: dict = {d: 0 for d in days}
day_members: dict = {d: 0 for d in days}
top_members = []

if cid:
    # Total active members
    try:
        total_members = supabase.table("community_members").select("id", count="exact").eq("community_id", cid).eq("is_active", True).execute().count or 0
    except Exception:
        pass

    # Posts flagged (7d)
    try:
        pr = supabase.table("posts").select("created_at").eq("community_id", cid).gte("created_at", since_str).execute()
        posts_data = pr.data or []
        posts_flagged = len(posts_data)
        for row in posts_data:
            ts = pd.Timestamp(row["created_at"]).tz_convert("UTC").normalize()
            if ts in day_posts:
                day_posts[ts] += 1
    except Exception:
        pass

    # Posts removed (7d)
    try:
        rr = supabase.table("moderation_logs").select("created_at").eq("community_id", cid).eq("action_taken", "remove").gte("created_at", since_str).execute()
        for row in rr.data or []:
            posts_removed += 1
            ts = pd.Timestamp(row["created_at"]).tz_convert("UTC").normalize()
            if ts in day_removed:
                day_removed[ts] += 1
    except Exception:
        pass

    # Matches (7d)
    try:
        mr = supabase.table("matches").select("requested_at").eq("community_id", cid).gte("requested_at", since_str).execute()
        for row in mr.data or []:
            total_matches += 1
            ts = pd.Timestamp(row["requested_at"]).tz_convert("UTC").normalize()
            if ts in day_matches:
                day_matches[ts] += 1
    except Exception:
        pass

    # New members (7d)
    try:
        nmr = supabase.table("community_members").select("joined_at").eq("community_id", cid).gte("joined_at", since_str).execute()
        for row in nmr.data or []:
            ts_raw = row.get("joined_at")
            if ts_raw:
                try:
                    ts = pd.Timestamp(ts_raw).tz_convert("UTC").normalize()
                except Exception:
                    ts = pd.Timestamp(ts_raw).normalize()
                if ts in day_members:
                    day_members[ts] += 1
    except Exception:
        pass

    # OG Members
    try:
        og_r = supabase.table("community_members").select(
            "users(display_name, warning_count, status)"
        ).eq("community_id", cid).eq("is_active", True).order("joined_at", desc=False).limit(5).execute()
        top_members = [(m.get("users") or {}) for m in (og_r.data or []) if m.get("users")]
    except Exception:
        pass

# ── Stats cards ───────────────────────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
s1.metric("Total Members", f"{total_members:,}")
s2.metric("Posts Flagged (7d)", posts_flagged)
s3.metric("Posts Removed (7d)", posts_removed)
s4.metric("Matches (7d)", total_matches)

st.divider()


def make_chart_df(day_dict: dict) -> pd.DataFrame:
    labels = [d.strftime("%d %b") for d in days]
    values = [day_dict[d] for d in days]
    return pd.DataFrame({"วัน": labels, "Count": values}).set_index("วัน")


# ── Posts Flagged chart ────────────────────────────────────────────────────────
st.subheader("📊 Posts Flagged (7 วัน)")
st.bar_chart(make_chart_df(day_posts))

# ── Matches chart ──────────────────────────────────────────────────────────────
st.subheader("⚔️ Matches (7 วัน)")
st.bar_chart(make_chart_df(day_matches))

# ── New Members chart ──────────────────────────────────────────────────────────
st.subheader("📈 New Members (7 วัน)")
st.bar_chart(make_chart_df(day_members))

st.divider()

# ── OG Members ────────────────────────────────────────────────────────────────
st.subheader("🏆 OG Members (joined earliest)")

if not top_members:
    st.info("ยังไม่มีข้อมูล")
else:
    for i, m in enumerate(top_members):
        name = m.get("display_name", "—")
        status_val = m.get("status", "active") or "active"
        warning_count = m.get("warning_count", 0) or 0
        rank_icon = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else f"{i + 1}."
        warn_badge = "✅ Clean" if warning_count == 0 else f"⚠️ {warning_count} warns"
        st.markdown(
            f"{rank_icon} **{name}** · {status_val.capitalize()} · {warn_badge}"
        )
