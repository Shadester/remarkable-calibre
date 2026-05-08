from typing import Optional, Tuple


def pick_format(available: set, priority: list) -> Tuple[Optional[str], Optional[str]]:
    """Return (format_string, None) for the best available format per priority order.

    Returns (None, reason_string) when no supported format is available.
    priority entries and available entries are matched case-insensitively.
    """
    upper_available = {f.upper() for f in available}
    for fmt in priority:
        if fmt.upper() in upper_available:
            return fmt.upper(), None
    if not available:
        return None, 'Book has no formats'
    return None, f'No supported format found (available: {", ".join(sorted(available))})'
