import logging
import logging.config

logging.config.fileConfig('~/Documents/GitHub/Joes-Python-Ideas/logging.conf')

logger = logging.getLogger('simpleExample')

def hello_world(name:str = 'Joe', log_level:str = 'INFO') -> str:
    """Hello World function that prints 'Hello World, name', 
        after calling a few unnecessary functions to test the logs."""
    logger.info('log1.hello_world() has begun')
    output = 'Hello World, and Hello {name}'
    logger.debug(output)
    formatted_output = output.format(name=name)
    logger.debug(formatted_output)
    return formatted_output