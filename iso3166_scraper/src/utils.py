import time
import logging
from unidecode import unidecode
import re
from pathlib import Path
from config.logger import get_logger

logger = get_logger(__name__)

def measure_execution_time(func) :
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        res = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logger.info(f"{func.__name__} - elapsed time: {elapsed_time:.3f}s")
        return res

    return wrapper

def none_if(expression_1: str, expression_2: str) -> (None | str):
    """
    The none_if() function returns None if two expressions are equal, otherwise it returns the first expression.
    """
    return None if expression_1 == expression_2 else expression_1

def async_measure_execution_time(async_func) :
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        res = await async_func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logger.info(f"{async_func.__name__} - elapsed time: {elapsed_time:.3f}s")
        return res

    return wrapper

def to_snake_case(s: str) -> str:
  
  s = unidecode(s) # remove accents
  s = s.replace(',', '')

  return '_'.join(
    re.sub('([A-Z][a-z]+)', r' \1',
    re.sub('([A-Z]+)', r' \1',
    s.replace('-', ' '))).split()).lower()

def save_file(file_path: Path, content: str) -> None:

    file_path.parent.mkdir(exist_ok=True, parents=True)

    with open(file_path, "w") as file:
        file.write(content)

    logger.info(f"{file_path} saved")
