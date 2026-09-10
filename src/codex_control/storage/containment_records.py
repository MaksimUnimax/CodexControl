"""Content-free durable metadata for local containment under UNKNOWN."""

from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class DeleteStorageContainmentRecord:
    dialogue_id: str
    profile_id: str
    thread_identity_sha256: str
    dialogue_version: int
    official_delete_authority: str
    local_isolated_storage_containment: str
    contained_at_ms: int

    def __repr__(self) -> str:
        return (
            "DeleteStorageContainmentRecord("
            f"dialogue_present={self.dialogue_id is not None!r}, "
            f"profile_present={self.profile_id is not None!r}, "
            f"thread_identity_present={bool(self.thread_identity_sha256)!r}, "
            f"dialogue_version={self.dialogue_version!r}, "
            f"official_delete_authority={self.official_delete_authority!r}, "
            f"local_isolated_storage_containment={self.local_isolated_storage_containment!r}, "
            f"contained_at_ms={self.contained_at_ms!r})"
        )
