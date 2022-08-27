import logging
import logging.config
from pathlib import Path

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create fileHandler and set level to DEBUG
fh = logging.FileHandler(filename='test.log')
fh.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(filename)s(%(lineno)s) - %(levelname)s - %(message)s')
formatter.datefmt = '%m/%d/%Y %H:%M:%S %Z(%z)'

# add formatter to fh
fh.setFormatter(formatter)

# add fh to logger
logger.addHandler(fh)

def hello_world(name:str = 'Joe', log_level:str = 'INFO') -> str:
    """Hello World function that prints 'Hello World, name', 
        after calling a few unnecessary functions to test the logs."""
    logger.info('log1.hello_world() has begun')
    logger.info(Path(__file__).parent)
    output = 'Hello World, and Hello {name}'
    logger.debug('output object: ' + output)
    formatted_output = output.format(name=name)
    logger.debug('formatted_output object: ' + formatted_output)
    return formatted_output