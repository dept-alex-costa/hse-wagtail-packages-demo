"""Tiny path helper for the release demo; not a production redirect system."""


def normalise_path(value: str) -> str:
    """Return a local absolute path while preserving trailing slashes."""
    path = value.strip()
    if ":" in path or path.startswith("//") or any(ord(char) < 32 for char in path):
        raise ValueError("Expected a local path")
    return "/" + path.lstrip("/")
