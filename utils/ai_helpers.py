import streamlit as st
import anthropic
import httpx
import json


# ── External AI API (guild-os-ai) ─────────────────────────────────────────────
# If AI_API_URL is set in secrets, calls are routed through the FastAPI service.
# Otherwise falls back to calling Anthropic directly.

@st.cache_resource
def get_ai_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


def _call_ai_api(endpoint: str, payload: dict) -> dict | None:
    url    = st.secrets.get("AI_API_URL", "")
    secret = st.secrets.get("AI_BOT_SECRET", "")
    if not url:
        return None
    try:
        r = httpx.post(
            f"{url.rstrip('/')}/{endpoint}",
            json=payload,
            headers={"x-bot-secret": secret},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data if data else None
    except Exception:
        return None


# ── Onboarding / Profiler ─────────────────────────────────────────────────────
def run_onboarding_ai(name: str, game: str, role: str, playtime: str) -> dict:
    # Route 1: guild-os-ai FastAPI → POST /onboarding
    result = _call_ai_api("onboarding", {
        "name": name, "game": game, "role": role, "playtime": playtime
    })
    if result:
        return result

    # Route 2: Direct Anthropic call (fallback)
    client = get_ai_client()
    prompt = f"""
คุณคือ AI Profiling Engine ของ GuildOS สร้าง Skill Card JSON สำหรับสมาชิกใหม่

ข้อมูลสมาชิก:
- ชื่อ: {name}
- เกม: {game}
- Role: {role}
- ช่วงเวลาที่เล่น: {playtime}

ตอบกลับเป็น JSON เท่านั้น:
{{
  "skill_level": "beginner|intermediate|advanced",
  "preferred_roles": ["..."],
  "playtime_slots": ["..."],
  "personality_tags": ["..."],
  "persona_tag": "class name in game",
  "engagement_score": 0-100,
  "onboarding_summary": "สรุปสั้นๆ ภาษาไทย 1 ประโยค"
}}
"""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(message.content[0].text)


# ── Matchmaker ────────────────────────────────────────────────────────────────
def run_matchmaker(request: str, game: str) -> dict:
    # Route 1: guild-os-ai FastAPI → POST /match
    result = _call_ai_api("match", {"request": request, "game": game})
    if result:
        return result

    # Route 2: Direct Anthropic call (fallback)
    client = get_ai_client()
    prompt = f"""
คุณคือ Smart Matchmaker AI ของ GuildOS วิเคราะห์คำขอหาทีม:

คำขอ: "{request}"
เกม: {game}

ตอบเป็น JSON เท่านั้น:
{{
  "parsed_request": {{
    "role_needed": "...",
    "time_window": "...",
    "constraints": []
  }},
  "matches": [
    {{
      "name": "ชื่อจำลอง",
      "role": "...",
      "score": 85,
      "playtime": "...",
      "reason": "เหตุผลที่เข้ากัน"
    }}
  ],
  "match_count": 3
}}

สร้างตัวอย่าง matches จำลอง 2-3 คนที่เหมาะสมกับคำขอ
"""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    result = _parse_json(message.content[0].text)
    if "matches" not in result:
        result["matches"] = []
    return result


# ── Moderator ─────────────────────────────────────────────────────────────────
def run_moderator(content: str, threshold: float = 0.7) -> dict:
    # Route 1: guild-os-ai FastAPI → POST /moderate
    result = _call_ai_api("moderate", {"content": content, "threshold": threshold})
    if result:
        return result

    # Route 2: Direct Anthropic call (fallback)
    client = get_ai_client()
    prompt = f"""
คุณคือ AI Moderator ของ GuildOS ตรวจสอบเนื้อหานี้:

"{content}"

ตอบเป็น JSON เท่านั้น:
{{
  "score": 0.0-1.0,
  "category": "spam|hate|toxic|scam|clean",
  "action": "remove|warn|approve",
  "reason": "เหตุผลสั้นๆ ภาษาไทย"
}}

threshold = {threshold} (score เกินนี้ = action เป็น remove หรือ warn)
"""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(message.content[0].text)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"raw_response": text}
