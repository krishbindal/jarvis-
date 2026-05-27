from abc import ABC, abstractmethod
from typing import Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)

class IoTBridge(ABC):
    """Abstract Base Class for Smart Hardware Bridges (e.g., Hue, Nest, Smart Plugs)."""
    
    @property
    @abstractmethod
    def bridge_name(self) -> str:
        """Name of the hardware bridge."""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Establish a connection to the hardware or central hub."""
        pass

    @abstractmethod
    def discover_devices(self) -> List[Dict[str, Any]]:
        """Return a list of devices accessible via this bridge."""
        pass

    @abstractmethod
    def execute_action(self, device_id: str, action: str, parameters: Dict[str, Any]) -> bool:
        """Send a control action to the specified device."""
        pass

# Registration System
_BRIDGES: Dict[str, IoTBridge] = {}

def register_bridge(bridge: IoTBridge):
    """Register a hardware bridge instance."""
    _BRIDGES[bridge.bridge_name.lower().replace(" ", "_")] = bridge
    logger.info(f"[HARDWARE] Registered bridge: {bridge.bridge_name}")

def get_bridge(name: str) -> IoTBridge | None:
    """Retrieve a registered bridge by name."""
    return _BRIDGES.get(name.lower().replace(" ", "_"))

def list_bridges() -> List[str]:
    """List all registered bridges."""
    return list(_BRIDGES.keys())

# Auto-initialize known bridges
def init_hardware():
    """Discover and initialize all available hardware bridges."""
    try:
        from hardware.hue_bridge import HueBridge
        hue = HueBridge()
        if hue.connect():
            register_bridge(hue)
    except ImportError:
        pass
    except Exception as exc:
        logger.error(f"[HARDWARE] Failed to init Hue bridge: {exc}")
