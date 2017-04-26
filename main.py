from core.bot import Red
from core.global_checks import init_global_checks
from core.events import init_events
from core.json_flusher import init_flusher
from core.settings import parse_cli_flags
import logging.handlers
import logging
import os
import sys

#
#               Red - Discord Bot v3
#
#         Made by Twentysix, improved by many
#


def init_loggers(cli_flags):
    dpy_logger = logging.getLogger("discord")
    dpy_logger.setLevel(logging.WARNING)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    dpy_logger.addHandler(console)

    logger = logging.getLogger("red")

    red_format = logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(red_format)

    if cli_flags.debug:
        os.environ['PYTHONASYNCIODEBUG'] = '1'
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    fhandler = logging.handlers.RotatingFileHandler(
        filename='red.log', encoding='utf-8', mode='a',
        maxBytes=10**7, backupCount=5)
    fhandler.setFormatter(red_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)

if __name__ == '__main__':
    cli_flags = parse_cli_flags()
    init_loggers(cli_flags)
    init_flusher()
    description = "Red v3 - Alpha"
    red = Red(cli_flags, description=description, pm_help=None)
    init_global_checks(red)
    init_events(red)
    red.load_extension('core')
    if cli_flags.dev:
        pass # load dev cog here?
    red.run(os.environ['RED_TOKEN'], bot=not cli_flags.not_bot)
