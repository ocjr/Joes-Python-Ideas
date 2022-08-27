import logging
import logging.config
from pathlib import Path
from log_test import log2

LOGGING_CONFIG = Path(__file__).parent /'config'/'logging.conf'
logging.config.fileConfig(LOGGING_CONFIG)

logger = logging.getLogger('simpleExample')

def hello_world(name:str = 'Joe', log_level:str = 'INFO') -> str:
    """Hello World function that prints 'Hello World, name', 
        after calling a few unnecessary functions to test the logs."""
    if log_level == 'INFO':
        logger.setLevel(logging.INFO)
    elif log_level == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARN)

    logger.info('log1.hello_world() has begun')
    output = 'Hello World, and Hello {name}'
    logger.debug('output object: ' + output)
    formatted_output = log2.joes_formatter(output, name, log_level)
    logger.debug('formatted_output object: ' + formatted_output)
    return formatted_output