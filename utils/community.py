"""Shared community helpers with 60-second session-state cache.

Each page previously made its own supabase.table("communities").select(...)
call on every rerun. This module centralises that query and caches the result
in st.session_state for 60 seconds — matching the TanStack Query staleTime
used in the Next.js version.
"""

import time
import streamlit as st
from utils.supabase_client import get_client
from components.auth import get_current_user

_FIELDS = "id, name, platform, platform_group_id, total_members, subscription_tier, matchmaker_config, is_onboarded"
_TTL = 60  # seconds


def get_community(bust: bool = False) -> dict | None:
    """Return the current user's community, cached for 60 s.

    Pass bust=True to force a fresh fetch (e.g. after save actions).
    """
    uid = get_current_user().get("id")
    if not uid:
        return None

    cache_key = f"_comm_{uid}"
    ts_key = f"_comm_{uid}_ts"
    now = time.time()

    if not bust and cache_key in st.session_state and (now - st.session_state.get(ts_key, 0)) < _TTL:
        return st.session_state[cache_key]

    try:
        r = get_client().table("communities").select(_FIELDS).eq("admin_auth_id", uid).limit(1).execute()
        community = r.data[0] if r.data else None
    except Exception:
        community = None

    st.session_state[cache_key] = community
    st.session_state[ts_key] = now
    return community
