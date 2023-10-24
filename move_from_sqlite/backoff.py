from functools import wraps
from logging import Logger
from time import sleep


def backoff(
    logger: Logger, start_sleep_time: float = 0.1, factor: float = 2, border_sleep_time: float = 10,
):
    """
    Функция для повторного выполнения функции через некоторое время,
    если возникла ошибка.
    Использует наивный экспоненциальный рост времени повтора (factor)
    до граничного времени ожидания (border_sleep_time)

    Формула:
        t = start_sleep_time * 2^(n) if t < border_sleep_time
        t = border_sleep_time if t >= border_sleep_time
    :param logger: Logger in application
    :param start_sleep_time: начальное время повтора
    :param factor: во сколько раз нужно увеличить время ожидания
    :param border_sleep_time: граничное время ожидания
    :return: результат выполнения функции
    """

    def func_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            sleep_time = start_sleep_time
            while True:
                try:
                    result = func(*args, **kwargs)
                    break
                except Exception as e:
                    logger.error(f'App stopped with error: {e}')
                    logger.info(f'Will retry in: {sleep_time} seconds')
                sleep(sleep_time)
                new_sleep_time = sleep_time * 2 ** factor
                sleep_time = new_sleep_time if new_sleep_time < border_sleep_time else border_sleep_time
            return result

        return inner

    return func_wrapper
