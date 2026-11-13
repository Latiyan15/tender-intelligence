def __getattr__(name):
    if name == "DiscoveryService":
        from src.services.discovery_service import DiscoveryService
        return DiscoveryService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["DiscoveryService"]
