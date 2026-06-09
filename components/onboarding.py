import streamlit as st
from utils.supabase_client import get_client
from utils.ai_helpers import _call_ai_api
from components.auth import get_current_user

GAMES = ["ROV", "Valorant", "PUBG", "League of Legends", "Dota 2", "Genshin Impact", "อื่นๆ"]
ROLES = ["Tank", "Support", "Carry", "Mid", "Jungle", "Flex", "อื่นๆ"]
TIME_SLOTS = ["เช้า (06-12)", "บ่าย (12-18)", "เย็น (18-22)", "ดึก (22-01)", "ดึกมาก (01-06)"]
PLAY_STYLES = ["Aggressive", "Teamwork", "Competitive", "Casual"]
GOALS = [
    ("rank_push",  "Push Rank"),
    ("casual",     "Casual Play"),
    ("tournament", "Tournament"),
    ("find_team",  "Find Team"),
]


def render_onboarding():
    supabase = get_client()
    user = get_current_user()
    uid = user.get("id")

    try:
        comm_r = supabase.table("communities").select(
            "id, name, platform, platform_group_id, total_members"
        ).eq("admin_auth_id", uid).limit(1).execute()
        community = comm_r.data[0] if comm_r.data else None
    except Exception:
        community = None

    if not community:
        st.error("ไม่พบข้อมูลชุมชน")
        return

    cid = community["id"]

    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    .block-container { max-width: 600px !important; margin: 4vh auto !important; }
    </style>
    """, unsafe_allow_html=True)

    if "onb_step" not in st.session_state:
        st.session_state["onb_step"] = 1

    step = st.session_state["onb_step"]

    st.markdown("## ⚔️ GuildOS — ตั้งค่าชุมชน")
    st.progress(step / 4, text=f"ขั้นตอน {step} จาก 4")
    st.divider()

    if step == 1:
        _step1_community_info(supabase, cid, community)
    elif step == 2:
        _step2_gaming_profile(supabase, cid, uid, community)
    elif step == 3:
        _step3_webhook(community)
    elif step == 4:
        _step4_done(supabase, cid)


def _step1_community_info(supabase, cid, community):
    st.subheader("Step 1: ข้อมูลชุมชน")

    name = st.text_input("ชื่อชุมชน", value=community.get("name", ""))
    st.text_input(
        "Platform",
        value=(community.get("platform") or "").capitalize(),
        disabled=True,
        help="ตั้งค่าตอนสมัครสมาชิก ไม่สามารถเปลี่ยนได้",
    )
    member_count = st.number_input(
        "จำนวนสมาชิกโดยประมาณ",
        min_value=1,
        value=int(community.get("total_members") or 10),
        step=10,
    )

    if st.button("ถัดไป →", type="primary", use_container_width=True):
        if not name.strip():
            st.error("กรุณากรอกชื่อชุมชน")
            return
        try:
            supabase.table("communities").update({
                "name": name.strip(),
                "total_members": int(member_count),
            }).eq("id", cid).execute()
            st.session_state["onb_step"] = 2
            st.rerun()
        except Exception as e:
            st.error(f"บันทึกไม่สำเร็จ: {e}")


def _step2_gaming_profile(supabase, cid, uid, community):
    st.subheader("Step 2: Gaming Profile")
    st.caption("กำหนดโปรไฟล์เกมของชุมชน — ใช้สำหรับ AI Matchmaker")

    game = st.selectbox("เกมหลัก", GAMES)
    role = st.selectbox("Role", ROLES)
    available_time = st.multiselect(
        "ช่วงเวลาที่เล่น",
        TIME_SLOTS,
        default=[TIME_SLOTS[2]],
    )
    play_style = st.selectbox("Play Style", PLAY_STYLES)
    goal_ids = [g[0] for g in GOALS]
    goal_labels = [g[1] for g in GOALS]
    goal_idx = st.selectbox("เป้าหมายหลัก", range(len(GOALS)), format_func=lambda i: goal_labels[i])
    goal = goal_ids[goal_idx]
    rank = st.text_input("Rank (ไม่บังคับ)", placeholder="เช่น Diamond, Platinum")

    col1, col2 = st.columns(2)
    if col1.button("← ย้อนกลับ", use_container_width=True):
        st.session_state["onb_step"] = 1
        st.rerun()

    if col2.button("ถัดไป →", type="primary", use_container_width=True):
        if not available_time:
            st.error("กรุณาเลือกช่วงเวลาที่เล่นอย่างน้อย 1 ช่วง")
            return
        with st.spinner("กำลังสร้าง AI Profile..."):
            payload = {
                "community_id": cid,
                "auth_user_id": uid,
                "platform": community.get("platform", ""),
                "game": game,
                "role": role,
                "available_time": available_time,
                "play_style": play_style,
                "goal": goal,
            }
            if rank.strip():
                payload["rank"] = rank.strip()

            result = _call_ai_api("onboarding", payload) or {}

            skill_card_data = {
                "community_id": cid,
                "user_id": uid,
                "game": game,
                "role": role,
                "play_style": play_style,
                "goal": goal,
            }
            if rank.strip():
                skill_card_data["rank"] = rank.strip()
            if result.get("time_vector"):
                skill_card_data["time_vector"] = result["time_vector"]
            if result.get("style_vector"):
                skill_card_data["style_vector"] = result["style_vector"]

            try:
                supabase.table("skill_cards").upsert(
                    skill_card_data, on_conflict="community_id,user_id"
                ).execute()
            except Exception:
                try:
                    supabase.table("skill_cards").insert(skill_card_data).execute()
                except Exception:
                    pass

            st.session_state["onb_step"] = 3
            st.rerun()


def _step3_webhook(community):
    st.subheader("Step 3: เชื่อมต่อ Webhook")
    platform = community.get("platform", "")
    platform_group_id = community.get("platform_group_id", "")
    webhook_url = f"https://api.guildos.app/api/webhook/{platform}/{platform_group_id}"

    st.markdown(f"คัดลอก URL ด้านล่างและตั้งค่าใน **{platform.capitalize()}** ของคุณ")
    st.code(webhook_url, language=None)

    if platform == "discord":
        with st.expander("📋 วิธีตั้งค่า Discord Webhook"):
            st.markdown("""
1. เปิด Server Settings → Integrations → Webhooks
2. สร้าง Webhook ใหม่ หรือใช้อันที่มีอยู่
3. วาง URL ด้านบนในช่อง Webhook URL แล้วกด Save
            """)
    elif platform == "line":
        with st.expander("📋 วิธีตั้งค่า LINE Webhook"):
            st.markdown("""
1. เข้า LINE Developers Console → Provider → Channel ของคุณ
2. ไปที่ Messaging API → Webhook settings
3. วาง URL ด้านบนแล้วกด Update และ Verify
            """)
    elif platform == "facebook":
        with st.expander("📋 วิธีตั้งค่า Facebook Webhook"):
            st.markdown("""
1. เข้า Meta for Developers → Apps ของคุณ
2. ไปที่ Webhooks → Page → Subscribe
3. วาง URL ด้านบนใน Callback URL
            """)

    col1, col2 = st.columns(2)
    if col1.button("← ย้อนกลับ", use_container_width=True, key="onb3_back"):
        st.session_state["onb_step"] = 2
        st.rerun()
    if col2.button("ถัดไป →", type="primary", use_container_width=True, key="onb3_next"):
        st.session_state["onb_step"] = 4
        st.rerun()


def _step4_done(supabase, cid):
    st.subheader("Step 4: เสร็จสิ้น! 🎉")
    st.success("ชุมชนของคุณพร้อมใช้งานแล้ว")
    st.markdown("""
**ระบบของคุณพร้อมแล้ว:**
- ✅ ข้อมูลชุมชนครบถ้วน
- ✅ Gaming Profile และ AI Vectors สร้างแล้ว
- ✅ Webhook URL พร้อมเชื่อมต่อ
- ✅ AI Moderation และ Matchmaker พร้อมทำงาน
    """)

    if st.button("เข้าสู่ Dashboard →", type="primary", use_container_width=True):
        try:
            supabase.table("communities").update({"is_onboarded": True}).eq("id", cid).execute()
        except Exception:
            pass
        st.session_state["onb_step"] = 1
        st.session_state["_onboarding_done"] = True
        # Bust community cache so app.py re-fetches updated is_onboarded
        for k in list(st.session_state.keys()):
            if k.startswith("_comm_cache"):
                del st.session_state[k]
        st.rerun()
