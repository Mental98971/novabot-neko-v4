"""
Structlog wrapper.

The rest of NovaBot calls `structlog.get_logger()` directly; the modules
ported from harmony-music-bot (the live-music engine) import
`get_logger(__name__)` from here instead. Both end up as the same
structlog logger, configured once in bot.core.bot.setup_logging().
"""
import structlog


def get_logger(name: str = __name__):
    return structlog.get_logger(name)
