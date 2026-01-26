def _format_duration(seconds: float) -> str:
    """Format seconds into readable string (e.g. 2h 30m 15s)"""
    if not seconds:
        return "0s"

    # Check for bad data (e.g. timestamps or nanoseconds)
    # If > 50 years (approx 1.5 billion seconds), assuming it's a timestamp or garbage -> 0
    if seconds > 1577880000:
        return "Invalid"

    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    parts = []
    if d > 0:
        parts.append(f"{d}d")
    if h > 0:
        parts.append(f"{h}h")
    if m > 0:
        parts.append(f"{m}m")
    if s > 0 or not parts:
        parts.append(f"{s}s")

    return " ".join(parts[:2])  # Return max 2 significant parts


def _format_size(size_bytes: int) -> str:
    if not size_bytes:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


if __name__ == "__main__":
    print(f"Format 120s: {_format_duration(120)}")
    print(f"Format 3661s: {_format_duration(3661)}")
    print(f"Format 0s: {_format_duration(0)}")
    print(f"Format Large (Invalid): {_format_duration(2000000000)}")
    print(f"Format Size 1024: {_format_size(1024)}")
    print(f"Format Size 1.5MB: {_format_size(1.5 * 1024 * 1024)}")
    print("Success")
