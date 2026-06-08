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

st.title("Members")
st.caption("สมาชิกทั้งหมดในชุมชน พร้อมสถานะและข้อมูลจากแพลตฟอร์ม")

# ── Fetch members ─────────────────────────────────────────────────────────────
try:
    q = supabase.table("community_members").select(
        "id, role, joined_at, is_active, users(id, display_name, platform_type, warning_count, status, last_active_at)"
    ).eq("is_active", True).order("joined_at", desc=True)
    if cid:
        q = q.eq("community_id", cid)
    members = q.execute().data or []
except Exception as e:
    st.error(f"โหลดข้อมูลไม่ได้: {e}")
    members = []

# ── Filters ────────────────────────────────────────────────────────────────────
roles = sorted({m.get("role", "") for m in members if m.get("role")})

f1, f2 = st.columns([3, 1])
search = f1.text_input("🔍 Search by name...", placeholder="ค้นหาชื่อสมาชิก")
role_filter = f2.selectbox("Role", ["All roles"] + roles)

filtered = [
    m for m in members
    if (search.lower() in (m.get("users") or {}).get("display_name", "").lower() or not search)
    and (role_filter == "All roles" or m.get("role") == role_filter)
]


def status_color(status: str) -> str:
    if status == "banned":
        return "🔴"
    elif status in ("muted", "warned"):
        return "🟠"
    return "🟢"


def warn_color(count: int) -> str:
    if count >= 3:
        return "text-red"
    elif count >= 1:
        return "orange"
    return "green"


# ── Detail dialog ─────────────────────────────────────────────────────────────
@st.dialog("Member Profile", width="large")
def show_member(m):
    u = m.get("users") or {}
    name = u.get("display_name", "—")
    role = m.get("role", "—")
    joined = m.get("joined_at", "")
    try:
        joined = pd.Timestamp(joined).strftime("%d/%m/%Y") if joined else "—"
    except Exception:
        pass
    last_active = u.get("last_active_at", "")
    try:
        last_active = pd.Timestamp(last_active).strftime("%d/%m/%Y %H:%M") if last_active else "—"
    except Exception:
        pass
    warning_count = u.get("warning_count", 0) or 0
    status_val = u.get("status", "active") or "active"

    st.markdown(f"## {name}")
    st.caption(role.capitalize())
    st.divider()

    rows = [
        ("Platform", u.get("platform_type", "—")),
        ("Role", role.capitalize()),
        ("Joined", joined),
        ("Last Active", last_active),
        ("Status", status_val.capitalize()),
    ]
    for label, val in rows:
        c1, c2 = st.columns([1, 2])
        c1.markdown(f"**{label}**")
        c2.markdown(val)

    st.divider()
    warn_icon = "🔴" if warning_count >= 3 else "🟠" if warning_count >= 1 else "🟢"
    st.metric(f"{warn_icon} Warning Count", warning_count)

    if warning_count == 0:
        st.success("No violations — Clean Record")
    elif warning_count >= 3:
        st.error("At risk of ban")
    else:
        st.warning("Has prior warnings")


# ── Member grid ───────────────────────────────────────────────────────────────
if not filtered:
    st.info("ไม่พบสมาชิกที่ตรงกับเงื่อนไข")
    st.stop()

st.caption(f"แสดง {len(filtered)} สมาชิก")

CARDS_PER_ROW = 4
rows = [filtered[i:i + CARDS_PER_ROW] for i in range(0, len(filtered), CARDS_PER_ROW)]

for row in rows:
    cols = st.columns(CARDS_PER_ROW)
    for col, m in zip(cols, row):
        u = m.get("users") or {}
        name = u.get("display_name", "—")
        role = m.get("role", "—")
        status_val = u.get("status", "active") or "active"
        platform = u.get("platform_type", "—")
        warning_count = u.get("warning_count", 0) or 0
        initials = name[:2].upper() if name != "—" else "?"

        s_icon = status_color(status_val)
        w_icon = "🔴" if warning_count >= 3 else "🟠" if warning_count >= 1 else "🟢"

        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align:center; font-size:2rem; "
                    f"background:linear-gradient(135deg,#6366f1,#06b6d4); "
                    f"border-radius:50%; width:48px; height:48px; "
                    f"display:flex; align-items:center; justify-content:center; "
                    f"margin:0 auto 8px; font-weight:bold; color:#fff'>"
                    f"{initials}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{name}**", help=role)
                st.caption(role.capitalize())
                st.markdown(
                    f"{s_icon} {status_val.capitalize()}  ·  `{platform}`"
                )
                st.caption(f"Warnings: {w_icon} {warning_count}")
                if st.button("View", key=f"member_view_{m.get('id', name)}", use_container_width=True):
                    show_member(m)
