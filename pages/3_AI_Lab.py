import streamlit as st
from components.auth import require_auth

require_auth()

st.title("🤖 AI Lab")
st.caption("ทดสอบและ tune AI agents ทั้ง 3 ตัว")

tab1, tab2, tab3 = st.tabs(["🛡️ Moderator", "🎮 Matchmaker", "🧬 Profiler"])

# ── Tab 1: AI Moderator ───────────────────────────────────────────────────────
with tab1:
    st.subheader("AI Moderator")
    st.caption("ทดสอบว่า AI จะ flag เนื้อหานี้ไหม")

    threshold = st.slider("Moderation Threshold", 0.0, 1.0, 0.7, 0.05,
                           help="score เกินค่านี้ = remove/warn")

    content = st.text_area("เนื้อหาที่ต้องการทดสอบ",
                            placeholder="เช่น: ขาย ID ราคาถูก ติดต่อ Line xxx",
                            height=120)

    if st.button("🔍 วิเคราะห์", key="mod_run", use_container_width=True):
        if not content:
            st.warning("กรุณาใส่เนื้อหา")
        else:
            try:
                from utils.ai_helpers import run_moderator
                with st.spinner("AI กำลังวิเคราะห์..."):
                    result = run_moderator(content, threshold)

                score    = result.get("score", 0)
                category = result.get("category", "—")
                action   = result.get("action", "—")
                reason   = result.get("reason", "—")

                color = {"remove": "🔴", "warn": "🟡", "approve": "🟢"}.get(action, "⚪")
                st.markdown(f"### {color} Action: `{action}`")

                c1, c2 = st.columns(2)
                c1.metric("Score", f"{score:.0%}")
                c2.metric("Category", category)
                st.info(f"**เหตุผล:** {reason}")
            except Exception as e:
                st.error(f"AI error: {e}")

# ── Tab 2: Matchmaker ─────────────────────────────────────────────────────────
with tab2:
    st.subheader("Smart Matchmaker")
    st.caption("ทดสอบการแปลงภาษาธรรมชาติเป็น match request")

    with st.form("match_form"):
        request_text = st.text_area(
            "คำขอหาทีม",
            placeholder="เช่น: หาตี้ตีป้อม ROV ช่วง 3 ทุ่ม ขอสายซัพพอร์ต ไม่เอาเด็ก",
            height=100,
        )
        game = st.selectbox("Game", ["ROV", "MLBB", "Valorant", "PUBG Mobile", "LoL"])
        run_match = st.form_submit_button("🎮 Run Matchmaker", use_container_width=True)

    if run_match and request_text:
        try:
            from utils.ai_helpers import run_matchmaker
            with st.spinner("AI กำลังวิเคราะห์..."):
                result = run_matchmaker(request_text, game)

            parsed = result.get("parsed_request", {})
            st.subheader("Parsed Request")
            col1, col2 = st.columns(2)
            col1.metric("Role Needed",  parsed.get("role_needed", "—"))
            col2.metric("Time Window",  parsed.get("time_window", "—"))
            if parsed.get("constraints"):
                st.caption(f"Constraints: {', '.join(parsed['constraints'])}")

            st.subheader(f"Matches ({result.get('match_count', 0)} คน)")
            for m in result.get("matches", []):
                with st.expander(f"👤 {m.get('name','?')} — {m.get('role','?')} · {m.get('score','?')}%"):
                    st.write(f"**Playtime:** {m.get('playtime','—')}")
                    st.write(f"**เหตุผล:** {m.get('reason','—')}")
        except Exception as e:
            st.error(f"AI error: {e}")

# ── Tab 3: Profiler ───────────────────────────────────────────────────────────
with tab3:
    st.subheader("Profiling Engine")
    st.caption("ทดสอบการสร้าง Skill Card จากข้อมูลสมาชิก")

    with st.form("profile_form"):
        name     = st.text_input("ชื่อสมาชิก")
        game     = st.selectbox("Game", ["ROV", "MLBB", "Valorant", "PUBG Mobile", "LoL"])
        role     = st.text_input("Role / สาย", placeholder="เช่น สายซัพพอร์ต, Jungler, ADC")
        playtime = st.selectbox("ช่วงเวลาที่เล่น", ["กลางวัน", "กลางคืน", "ทุกช่วง"])
        run_profile = st.form_submit_button("🧬 Generate Skill Card", use_container_width=True)

    if run_profile and name:
        try:
            from utils.ai_helpers import run_onboarding_ai
            with st.spinner("AI กำลังสร้าง Skill Card..."):
                result = run_onboarding_ai(name, game, role, playtime)

            st.success("Skill Card สร้างสำเร็จ!")
            c1, c2, c3 = st.columns(3)
            c1.metric("Skill Level",      result.get("skill_level", "—"))
            c2.metric("Engagement Score", result.get("engagement_score", "—"))
            c3.metric("Persona Tag",      result.get("persona_tag", "—"))

            col_a, col_b = st.columns(2)
            col_a.markdown(f"**Preferred Roles:** {', '.join(result.get('preferred_roles', []))}")
            col_b.markdown(f"**Playtime:** {', '.join(result.get('playtime_slots', []))}")
            st.markdown(f"**Tags:** {', '.join(result.get('personality_tags', []))}")
            st.info(result.get("onboarding_summary", ""))

            with st.expander("Raw JSON"):
                st.json(result)
        except Exception as e:
            st.error(f"AI error: {e}")
