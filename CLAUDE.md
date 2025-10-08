# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal learning and experimentation repository containing Python scripts and tools for various ideas. The repository includes:

- **log_test**: A Python package for testing and learning about logging functionality
- **openai**: OpenAI integration scripts (resume editing tool)
- **client-1, client-2**: Git submodules for client-specific code

## Package Information

The main package is `logging_learning` (version 0.0.45), configured in `setup.py`.

## Project Structure

### log_test Package

The logging test package demonstrates hierarchical logging configuration:

- Entry point: `log_test/log1.py` - Contains `hello_world()` function that demonstrates logging at different levels
- Helper module: `log_test/log2.py` - Contains `joes_formatter()` utility for string formatting with logging
- Configuration: `log_test/config/logging.conf` - Centralized logging configuration using `logging.config.fileConfig()`
- Logger name: `simpleExample` - Shared across modules
- Log output: `test_log.log` - File handler configured in logging.conf
- Nested package: `log_test/log_test_1/` - Sub-package for additional logging experiments

Key architecture pattern: The logging configuration is loaded once in log1.py using `Path(__file__).parent / 'config' / 'logging.conf'`, and the same named logger (`simpleExample`) is retrieved across different modules to maintain consistent logging behavior.

### openai Package

- `openai/resume.py`: Resume editing suggestions using OpenAI API (uses deprecated `text-davinci-002` engine with `openai.Completion.create()`)

## Development Commands

### Installation
```bash
python setup.py install
# or for development mode
python setup.py develop
```

### Running the logging example
```python
from log_test import log1
result = log1.hello_world(name='YourName', log_level='DEBUG')
```

### Testing OpenAI integration
The resume.py script requires:
1. Setting `openai.api_key` in the code or environment
2. Providing paths to resume and job description files
3. Running: `python openai/resume.py`

## Important Notes

- The repository uses git submodules for client-specific code (client-1, client-2)
- Logging configuration uses file-based config (logging.conf) rather than dictConfig
- The openai/resume.py uses deprecated OpenAI API methods and may need updating to current SDK
