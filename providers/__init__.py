from .base import BaseProvider
from .string_adapter import StringProvider
from .scrapfly_adapter import ScrapflyProvider
from .alterlab_adapter import AlterLabProvider
from .context_dev_adapter import ContextDevProvider
from .pure_http_adapter import PureHttpProvider
from .session_assisted_http_adapter import SessionAssistedHttpProvider

def get_all_providers():
    return [
        PureHttpProvider(),
        SessionAssistedHttpProvider(),
        StringProvider(),
        ScrapflyProvider(),
        AlterLabProvider(),
        ContextDevProvider()
    ]

__all__ = [
    "BaseProvider",
    "PureHttpProvider",
    "SessionAssistedHttpProvider",
    "StringProvider",
    "ScrapflyProvider",
    "AlterLabProvider",
    "ContextDevProvider",
    "get_all_providers"
]
