"""Explicit profile lookup; no profile state is copied or merged."""
from .domain import CodexProfile


def profile_by_id(profiles: tuple[CodexProfile, ...], profile_id: str) -> CodexProfile:
    for profile in profiles:
        if profile.profile_id == profile_id:
            return profile
    raise KeyError(f"unknown profile_id: {profile_id}")
