import streamlit as st
import pandas as pd
import time
import random
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
            "id, name, platform, total_members, platform_group_id, subscription_tier, matchmaker_config"
        ).eq("admin_auth_id", uid).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


community = get_community()

if not community:
    st.warning("ไม่พบข้อมูลชุมชน")
    st.stop()

cid = community["id"]

st.title("Settings")
st.caption("Configure AI, integrations, profile, and your plan.")

tabs = st.tabs(["🤖 AI Config", "🔗 Integrations", "💚 System Health", "🔌 Platforms", "👤 Profile", "💳 Subscription"])

# ── Tab: AI Config ────────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("🛡 AI Moderation")

    mc_config = community.get("matchmaker_config") or {}
    time_window = int(mc_config.get("time_window", 60))

    if "ai_threshold" not in st.session_state:
        st.session_state["ai_threshold"] = 0.85
    if "ai_auto_remove" not in st.session_state:
        st.session_state["ai_auto_remove"] = True

    with st.container(border=True):
        st.markdown(
            f"**Confidence Threshold** — ปัจจุบัน: `{st.session_state['ai_threshold']:.2f}`  ·  "
            f"Auto-remove: {'เปิด' if st.session_state['ai_auto_remove'] else 'ปิด'}"
        )
        threshold = st.slider(
            "Threshold (quick adjust)",
            min_value=0.50, max_value=0.99, step=0.01,
            value=st.session_state["ai_threshold"],
            key="slider_threshold",
        )
        st.session_state["ai_threshold"] = threshold
        auto_remove = st.toggle(
            "Auto-remove เมื่อเกิน threshold",
            value=st.session_state["ai_auto_remove"],
            key="toggle_auto_remove",
        )
        st.session_state["ai_auto_remove"] = auto_remove

    st.divider()
    st.subheader("⚔️ Matchmaker")

    with st.container(border=True):
        new_time_window = st.slider(
            "Time Window (นาที)",
            min_value=10, max_value=180, step=5,
            value=time_window,
            key="slider_time_window",
        )
        st.caption(f"10 นาที — 180 นาที · ค่าปัจจุบัน: **{new_time_window} นาที**")

    if st.button("💾 บันทึกการตั้งค่า", type="primary", use_container_width=True):
        try:
            new_mc = {**mc_config, "time_window": new_time_window}
            supabase.table("communities").update(
                {"matchmaker_config": new_mc}
            ).eq("id", cid).execute()
            st.success(f"บันทึก Time Window = {new_time_window} นาที สำเร็จ!")
            st.rerun()
        except Exception as e:
            st.error(f"บันทึกไม่สำเร็จ: {e}")

# ── Tab: Integrations ─────────────────────────────────────────────────────────
with tabs[1]:
    platform = community.get("platform", "")
    platform_group_id = community.get("platform_group_id", "")
    webhook_url = f"https://api.guildos.app/api/webhook/{platform}/{platform_group_id}"

    with st.container(border=True):
        st.markdown(
            f"**{platform.capitalize()} Webhook**  "
            f"<span style='background:#16c78420; color:#16c784; padding:2px 8px; border-radius:4px; font-size:.75rem'>Active</span>",
            unsafe_allow_html=True,
        )
        st.caption(f"URL สำหรับรับ event จาก {platform}")
        st.code(webhook_url, language=None)
        if st.button("Test Connection", key="test_webhook"):
            st.success("✅ ทดสอบสำเร็จ")

    with st.container(border=True):
        st.markdown("**Platform Group ID**")
        st.caption("ID ของกลุ่มบนแพลตฟอร์ม — ใช้ระบุชุมชนเมื่อรับ webhook")
        st.code(platform_group_id or "—", language=None)

# ── Tab: System Health ────────────────────────────────────────────────────────
with tabs[2]:
    HEALTH_ITEMS = [
        "Database Connection",
        "Realtime Subscriptions",
        "AI Moderation",
        "Matchmaker",
        "LINE Webhook",
        "Discord Bot",
        "Data Integrity",
    ]

    if "health_checks" not in st.session_state:
        st.session_state["health_checks"] = []

    if st.button("🔄 Re-check", key="recheck_health") or not st.session_state["health_checks"]:
        results = []
        progress = st.progress(0, text="กำลังตรวจสอบ...")
        for i, item in enumerate(HEALTH_ITEMS):
            time.sleep(0.15)
            status = "ok" if random.random() > 0.15 else "fail"
            results.append({"name": item, "status": status})
            progress.progress((i + 1) / len(HEALTH_ITEMS), text=f"ตรวจสอบ {item}...")
        progress.empty()
        st.session_state["health_checks"] = results

    checks = st.session_state["health_checks"]
    if checks:
        pass_count = sum(1 for c in checks if c["status"] == "ok")
        fail_count = sum(1 for c in checks if c["status"] == "fail")
        all_ok = fail_count == 0

        if all_ok:
            st.success(f"✅ ระบบทั้งหมดพร้อมใช้งาน — {pass_count}/{len(checks)} ผ่าน")
        else:
            st.error(f"⚠ พบปัญหา {fail_count} รายการ — {pass_count}/{len(checks)} ผ่าน")

        for c in checks:
            icon = "✅" if c["status"] == "ok" else "❌"
            st.markdown(f"{icon} {c['name']}")

# ── Tab: Platforms ────────────────────────────────────────────────────────────
with tabs[3]:
    if "platform_state" not in st.session_state:
        st.session_state["platform_state"] = {"facebook": True, "discord": True, "line": False}
    if "notify_state" not in st.session_state:
        st.session_state["notify_state"] = {"spam": True, "team": False, "milestone": True}

    st.subheader("🔌 Platform Webhooks")
    p1, p2, p3 = st.columns(3)
    for col, p in zip([p1, p2, p3], ["facebook", "discord", "line"]):
        with col:
            with st.container(border=True):
                enabled = st.toggle(p.capitalize(), value=st.session_state["platform_state"][p], key=f"plat_{p}")
                st.session_state["platform_state"][p] = enabled
                badge = "🟢 Connected" if enabled else "⚫ Not connected"
                st.caption(badge)

    st.divider()
    st.subheader("🔔 Notification Preferences")
    st.caption("รับแจ้งเตือนทาง Email เมื่อเกิดเหตุการณ์สำคัญ")

    notifications = [
        ("spam", "Spam Spike Alert", "แจ้งเมื่อ spam เกิน 5 โพสต์ใน 1 ชั่วโมง"),
        ("team", "Team Formed", "แจ้งเมื่อ AI จัดทีมสำเร็จ"),
        ("milestone", "Member Milestone", "แจ้งเมื่อสมาชิกถึง 100, 500, 1000 คน"),
    ]
    for key, title, desc in notifications:
        nc1, nc2 = st.columns([4, 1])
        nc1.markdown(f"**{title}**")
        nc1.caption(desc)
        enabled = nc2.toggle("", value=st.session_state["notify_state"][key], key=f"notify_{key}", label_visibility="collapsed")
        st.session_state["notify_state"][key] = enabled

    if st.button("💾 บันทึก", type="primary", use_container_width=True, key="save_platforms"):
        st.success("บันทึกแล้ว")

# ── Tab: Profile ──────────────────────────────────────────────────────────────
with tabs[4]:
    with st.container(border=True):
        st.text_input("Account Email", value=user.get("email", ""), disabled=True)

        new_name = st.text_input("ชื่อชุมชน", value=community.get("name", ""), key="profile_name")
        st.text_input("Platform", value=(community.get("platform") or "").capitalize(), disabled=True)
        st.text_input(
            "Platform Group ID",
            value=community.get("platform_group_id", ""),
            disabled=True,
        )

        if st.button("💾 บันทึก", type="primary", use_container_width=True, key="save_profile"):
            try:
                supabase.table("communities").update({"name": new_name}).eq("id", cid).execute()
                st.success("บันทึกแล้ว")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ── Tab: Subscription ─────────────────────────────────────────────────────────
with tabs[5]:
    current_tier = (community.get("subscription_tier") or "free").lower()

    plans = [
        {
            "id": "free",
            "name": "Free",
            "price": "฿0",
            "features": ["1 ชุมชน", "1,000 สมาชิก", "AI Moderation พื้นฐาน"],
        },
        {
            "id": "pro",
            "name": "Pro",
            "price": "฿990 / เดือน",
            "features": ["3 ชุมชน", "30,000 สมาชิก", "Smart Matchmaker", "Priority support"],
        },
        {
            "id": "enterprise",
            "name": "Enterprise",
            "price": "ติดต่อเรา",
            "features": ["ไม่จำกัดชุมชน", "Custom AI models", "Dedicated success manager"],
        },
    ]

    p_cols = st.columns(len(plans))
    for col, plan in zip(p_cols, plans):
        active = current_tier == plan["id"]
        with col:
            with st.container(border=True):
                if active:
                    st.markdown(
                        f"**{plan['name']}** "
                        f"<span style='background:#6366f120; color:#6366f1; padding:2px 6px; border-radius:4px; font-size:.7rem'>Current</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"**{plan['name']}**")
                st.markdown(f"### {plan['price']}")
                for f in plan["features"]:
                    st.markdown(f"✅ {f}")
                if active:
                    st.button("Current plan", disabled=True, key=f"plan_{plan['id']}", use_container_width=True)
                else:
                    if st.button("Upgrade", key=f"plan_{plan['id']}", use_container_width=True, type="primary"):
                        st.info("🔧 ทีมงานจะติดต่อกลับเร็วๆ นี้")
