import socket
from utils.logger import get_logger

logger = get_logger(__name__)

def is_online(host="8.8.8.8", port=53, timeout=2) -> bool:
    """
    Check if internet connectivity is available.
    Pings Google's public DNS by default.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False
    except Exception as e:
        logger.debug(f"[CONNECTIVITY] Unexpected error: {e}")
        return False
