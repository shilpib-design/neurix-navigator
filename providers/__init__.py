from .base import BaseProvider
from .string_adapter import StringProvider
from .scrapfly_adapter import ScrapflyProvider
from .alterlab_adapter import AlterLabProvider
from .context_dev_adapter import ContextDevProvider

def get_all_providers():
    return [
        StringProvider(),
        ScrapflyProvider(),
        AlterLabProvider(),
        ContextDevProvider()
    ]

__all__ = [
    "BaseProvider",
    "StringProvider",
    "ScrapflyProvider",
    "AlterLabProvider",
    "ContextDevProvider",
    "get_all_providers"
]
