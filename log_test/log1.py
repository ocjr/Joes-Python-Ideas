import logging
import logging.config
from pathlib import Path

LOGGING_CONFIG = Path(__file__).parent / 'logging.conf'
logging.config.fileConfig(LOGGING_CONFIG)

logger = logging.getLogger('simpleExample')
logger.setLevel('DEBUG')

def hello_world(name:str = 'Joe', log_level:str = 'INFO') -> str:
    """Hello World function that prints 'Hello World, name', 
        after calling a few unnecessary functions to test the logs."""
    logger.info('log1.hello_world() has begun')
    output = 'Hello World, and Hello {name}'
    logger.debug('output object: ' + output)
    formatted_output = output.format(name=name)
    logger.debug('formatted_output object: ' + formatted_output)
    return formatted_output