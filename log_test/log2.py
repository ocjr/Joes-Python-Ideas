import logging

logger = logging.getLogger('simpleExample')

def joes_formatter(phrase: str, inputs: str, log_level: str = 'INFO') -> str:
    """formats a phrase with an input"""

    if log_level == 'INFO':
        logger.setLevel(logging.INFO)
    elif log_level == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARN)

    logger.info('log2.joes_formatter has begun')
    output = phrase.format(name=inputs)
    logger.debug('output is: ' + output)
    return output