"""BR JARVIS legacy CLI entrypoint.

This module preserves historical references to main_mk37 while providing a
direct REPL-style CLI on top of the shared orchestrator runtime.

Improvements:
- orchestrator.shutdown() called on clean exit (consolidates memory)
- Signal handling via KeyboardInterrupt properly triggers shutdown
- readline history enabled on non-Windows for up-arrow command recall
"""
from __future__ import annotations

import asyncio
import sys
import os

from core.bootstrap import build_assistant_runtime


# Enable readline history on non-Windows systems for up-arrow command recall
if sys.platform != "win32":
    try:
        import readline  # noqa: F401
    except ImportError:
        pass


def _print_banner() -> None:
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(" BR JARVIS MK37 — Autonomous AI OS ")
    else:
        import logging
        logging.getLogger(__name__).info(" BR JARVIS MK37 — Autonomous AI OS ")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(" Type /quit to exit, /help for commands.")
    else:
        import logging
        logging.getLogger(__name__).info(" Type /quit to exit, /help for commands.")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(" Chat naturally or use /mode <name> to switch modes.")
    else:
        import logging
        logging.getLogger(__name__).info(" Chat naturally or use /mode <name> to switch modes.")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 60 }" if isinstance("=" * 60, str) else "=" * 60)


def _handle_command(cmd: str) -> bool:
    """Process slash commands. Returns False if exit was requested."""
    low = cmd.strip().lower()
    if low in {"/quit", "/exit", "quit", "exit"}:
        return False
    if low == "/help":
        if 'logger' in globals() or 'logger' in locals():
            logger.info("Commands:")
        else:
            import logging
            logging.getLogger(__name__).info("Commands:")
        if 'logger' in globals() or 'logger' in locals():
            logger.info("  /help         - Show this help")
        else:
            import logging
            logging.getLogger(__name__).info("  /help         - Show this help")
        if 'logger' in globals() or 'logger' in locals():
            logger.info("  /mode <name>  - Switch mode (recon, exploit, coder, analyst, general)")
        else:
            import logging
            logging.getLogger(__name__).info("  /mode <name>  - Switch mode (recon, exploit, coder, analyst, general)")
        if 'logger' in globals() or 'logger' in locals():
            logger.info("  /quit         - Exit CLI cleanly")
        else:
            import logging
            logging.getLogger(__name__).info("  /quit         - Exit CLI cleanly")
        if 'logger' in globals() or 'logger' in locals():
            logger.info("  /status       - Show backend status")
        else:
            import logging
            logging.getLogger(__name__).info("  /status       - Show backend status")
        return True
    return True


def main() -> None:
    orchestrator = None

    def _get_orchestrator():
        nonlocal orchestrator
        if orchestrator is None:
            runtime = build_assistant_runtime()
            orchestrator = runtime.orchestrator
        return orchestrator

    _print_banner()

    try:
        while True:
            try:
                user_input = input("you> ").strip()
            except EOFError:
                if 'logger' in globals() or 'logger' in locals():
                    logger.info("\nEOF received. Exiting CLI.")
                else:
                    import logging
                    logging.getLogger(__name__).info("\nEOF received. Exiting CLI.")
                break
            except KeyboardInterrupt:
                if 'logger' in globals() or 'logger' in locals():
                    logger.info("\n^C detected. Exiting cleanly...")
                else:
                    import logging
                    logging.getLogger(__name__).info("\n^C detected. Exiting cleanly...")
                break

            if not user_input:
                continue

            if user_input.startswith("/") or user_input.lower() in {"quit", "exit"}:
                if not _handle_command(user_input):
                    if 'logger' in globals() or 'logger' in locals():
                        logger.info("Exiting CLI.")
                    else:
                        import logging
                        logging.getLogger(__name__).info("Exiting CLI.")
                    break
                continue

            try:
                orc = _get_orchestrator()
                reply = orc.chat(user_input)
                if asyncio.iscoroutine(reply):
                    reply = asyncio.run(reply)
                if 'logger' in globals() or 'logger' in locals():
                    logger.info(f"{ f"jarvis> {reply}" }" if isinstance(f"jarvis> {reply}", str) else f"jarvis> {reply}")
                else:
                    import logging
                    logging.getLogger(__name__).info(f"{ f"jarvis> {reply}" }" if isinstance(f"jarvis> {reply}", str) else f"jarvis> {reply}")
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
    finally:
        # FIXED: Always call shutdown on exit so working memory is consolidated
        # and conversation store receives the end_session record.
        if orchestrator is not None:
            try:
                orchestrator.shutdown()
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        if 'logger' in globals() or 'logger' in locals():
            logger.info("👋 JARVIS shutdown complete.")
        else:
            import logging
            logging.getLogger(__name__).info("👋 JARVIS shutdown complete.")


if __name__ == "__main__":
    sys.exit(main() or 0)
