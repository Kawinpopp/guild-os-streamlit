import streamlit as st
from components.sidebar import render_sidebar
from utils.supabase_client import get_client

render_sidebar()

st.title("⚙️ Settings")
st.caption("ตั้งค่า community — plan, matchmaker และ onboarding")

supabase = get_client()

try:
    result = supabase.table("communities") \
        .select("id, name, platform, total_members, subscription_tier, is_onboarded, is_active, matchmaker_config, last_synced_at") \
        .order("name") \
        .execute()
    communities = result.data or []
except Exception as e:
    st.error(f"โหลดข้อมูลไม่ได้: {e}")
    communities = []

if not communities:
    st.info("ยังไม่มี community")
    st.stop()

community_names = [c["name"] for c in communities]
selected_name   = st.selectbox("เลือก Community", community_names)
selected        = next((c for c in communities if c["name"] == selected_name), None)

if not selected:
    st.stop()

st.divider()

mc_config = selected.get("matchmaker_config") or {"time_window": 60}

tab_general, tab_matchmaker, tab_plan = st.tabs(["General", "Matchmaker Config", "Plan"])

# ── Tab: General ──────────────────────────────────────────────────────────────
with tab_general:
    st.subheader("General Settings")

    with st.form("general_form"):
        new_name      = st.text_input("ชื่อ Community", value=selected.get("name", ""))
        new_platform  = st.selectbox(
            "Platform",
            ["facebook", "discord", "line"],
            index=["facebook", "discord", "line"].index(selected.get("platform", "facebook").lower())
                  if selected.get("platform", "").lower() in ["facebook", "discord", "line"] else 0,
        )
        new_onboarded = st.checkbox("Onboarded (เปิดใช้งานแล้ว)", value=bool(selected.get("is_onboarded")))
        new_active    = st.checkbox("Active",                       value=bool(selected.get("is_active", True)))
        save_general  = st.form_submit_button("💾 Save", use_container_width=True)

    if save_general:
        try:
            supabase.table("communities") \
                .update({
                    "name":         new_name,
                    "platform":     new_platform,
                    "is_onboarded": new_onboarded,
                    "is_active":    new_active,
                }) \
                .eq("id", selected["id"]) \
                .execute()
            st.success("บันทึกสำเร็จ!")
            st.rerun()
        except Exception as e:
            st.error(f"บันทึกไม่ได้: {e}")

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Members",  selected.get("total_members", 0))
    c2.metric("Platform",       selected.get("platform", "—"))
    c3.metric("Last Synced",    str(selected.get("last_synced_at", "—"))[:10])

# ── Tab: Matchmaker Config ────────────────────────────────────────────────────
with tab_matchmaker:
    st.subheader("Matchmaker Configuration")
    st.caption("ค่า config ที่ AI Matchmaker ใช้สำหรับ community นี้")

    st.json(mc_config)

    with st.form("matchmaker_form"):
        new_time_window = st.number_input(
            "Time Window (นาที) — ช่วงเวลาที่จะ match คน",
            min_value=10, max_value=1440,
            value=int(mc_config.get("time_window", 60)),
            step=10,
        )
        save_mc = st.form_submit_button("💾 Save Matchmaker Config", use_container_width=True)

    if save_mc:
        try:
            new_mc = {**mc_config, "time_window": new_time_window}
            supabase.table("communities") \
                .update({"matchmaker_config": new_mc}) \
                .eq("id", selected["id"]) \
                .execute()
            st.success(f"บันทึก time_window = {new_time_window} นาที สำเร็จ!")
            st.rerun()
        except Exception as e:
            st.error(f"บันทึกไม่ได้: {e}")

# ── Tab: Plan ─────────────────────────────────────────────────────────────────
with tab_plan:
    st.subheader("Subscription Plan")

    current_tier = selected.get("subscription_tier") or "free"

    PLAN_DETAILS = {
        "free":    {"price": 0,    "features": ["Moderation AI (basic)", "Up to 100 members"]},
        "starter": {"price": 490,  "features": ["Moderation AI", "Up to 500 members", "Basic analytics"]},
        "pro":     {"price": 1490, "features": ["All Starter", "Matchmaking AI", "Up to 5,000 members", "Data Insights"]},
    }

    cols = st.columns(len(PLAN_DETAILS))
    for col, (plan_name, detail) in zip(cols, PLAN_DETAILS.items()):
        is_current = (current_tier == plan_name)
        with col:
            st.markdown(f"### {'✅ ' if is_current else ''}{plan_name.capitalize()}")
            st.markdown(f"**฿{detail['price']:,}/เดือน**")
            for f in detail["features"]:
                st.markdown(f"- {f}")

    st.divider()

    with st.form("plan_form"):
        new_tier = st.selectbox(
            "เปลี่ยน Plan",
            list(PLAN_DETAILS.keys()),
            index=list(PLAN_DETAILS.keys()).index(current_tier)
                  if current_tier in PLAN_DETAILS else 0,
            format_func=str.capitalize,
        )
        save_plan = st.form_submit_button("💾 Upgrade / Downgrade", use_container_width=True)

    if save_plan:
        try:
            supabase.table("communities") \
                .update({"subscription_tier": new_tier}) \
                .eq("id", selected["id"]) \
                .execute()
            st.success(f"เปลี่ยนเป็น {new_tier.capitalize()} สำเร็จ!")
            st.rerun()
        except Exception as e:
            st.error(f"บันทึกไม่ได้: {e}")
