class ObservationError(ValueError):
    """No input was sent; refresh the observed state before retrying."""

class DesktopUnavailable(RuntimeError):
    """No physical input was sent because the interactive session is unavailable."""

class LocalInferenceDisabled(RuntimeError):
    """Persisted local inference setting is false, not an MCP transport failure."""
