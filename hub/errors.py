class ObservationError(ValueError):
    """No input was sent; refresh the observed state before retrying."""

class DesktopUnavailable(RuntimeError):
    """No physical input was sent because the interactive session is unavailable."""
