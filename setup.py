import subprocess
import sys

if 'logger' in globals() or 'logger' in locals():
    logger.info("Installing requirements...")
else:
    import logging
    logging.getLogger(__name__).info("Installing requirements...")
subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

if 'logger' in globals() or 'logger' in locals():
    logger.info("Installing Playwright browsers...")
else:
    import logging
    logging.getLogger(__name__).info("Installing Playwright browsers...")
subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)

if 'logger' in globals() or 'logger' in locals():
    logger.info("\n✅ Setup complete! Run 'python start.py' to start BR JARVIS.")
else:
    import logging
    logging.getLogger(__name__).info("\n✅ Setup complete! Run 'python start.py' to start BR JARVIS.")

