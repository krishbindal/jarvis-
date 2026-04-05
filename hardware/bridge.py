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
