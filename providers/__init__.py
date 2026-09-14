from .base import BaseProvider
from .string_adapter import StringProvider
from .scrapfly_adapter import ScrapflyProvider
from .alterlab_adapter import AlterLabProvider
from .context_dev_adapter import ContextDevProvider
from .pure_http_adapter import PureHttpProvider

def get_all_providers():
    return [
        PureHttpProvider(),
        StringProvider(),
        ScrapflyProvider(),
        AlterLabProvider(),
        ContextDevProvider()
    ]

__all__ = [
    "BaseProvider",
    "PureHttpProvider",
    "StringProvider",
    "ScrapflyProvider",
    "AlterLabProvider",
    "ContextDevProvider",
    "get_all_providers"
]
