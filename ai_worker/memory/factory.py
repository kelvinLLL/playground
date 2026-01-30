from typing import Dict, Optional
from ai_worker.memory.base import BaseMemoryProvider
from ai_worker.memory.providers.local_json import LocalJSONProvider

class MemoryFactory:
    """Factory for creating memory provider instances."""
    
    @staticmethod
    async def create(provider_name: str = "local", config: Optional[Dict] = None) -> BaseMemoryProvider:
        """
        Create and initialize a memory provider.
        
        Args:
            provider_name: "local", "memu", "mem0"
            config: Configuration dictionary
            
        Returns:
            Initialized memory provider
        """
        provider = None
        
        if provider_name == "local":
            # Config could specify file path
            file_path = config.get("file_path", "ai_worker_local_memory.json") if config else "ai_worker_local_memory.json"
            provider = LocalJSONProvider(file_path=file_path)
            
        elif provider_name == "memu":
            try:
                from ai_worker.memory.providers.memu import MemUProvider
                provider = MemUProvider(config)
            except ImportError as e:
                print(f"Failed to import MemUProvider: {e}")
                provider = LocalJSONProvider()
        
        else:
            # Fallback to local for safety, or raise error
            print(f"Warning: Unknown provider '{provider_name}', falling back to local.")
            provider = LocalJSONProvider()
            
        await provider.initialize()
        return provider
