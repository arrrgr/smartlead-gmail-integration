"""
Smartlead-Attio Integration Package
"""
from .attio_client import AttioClient
from .smartlead_attio_sync import SmartleadAttioSync

__version__ = "1.0.0"
__all__ = ["AttioClient", "SmartleadAttioSync"] 