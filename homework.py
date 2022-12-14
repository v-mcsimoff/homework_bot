import logging
import os
import json
import sys

import requests
import time
import telegram

from dotenv import load_dotenv
from http import HTTPStatus

import exceptions


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s',
    handlers=[logging.FileHandler('main.log', 'w', encoding='utf-8'),
              logging.StreamHandler(sys.stdout)]
    )


def check_tokens():
    """проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    try:
        logging.info('Отправляем сообщение')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено')
    except telegram.error.TelegramError as error:
        error_message = f'Ошибка при отправке сообщения: {error}'
        logging.error(f"Ошибка {error_message}")
        # переписали тесты и без этого логгирования они не проходят :(
        # но надеюсь, что принцип я правильно понял
        raise exceptions.SendMessageException(error_message)


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=headers, params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise exceptions.GetAPIException('Статус запроса не 200')
    except requests.RequestException as error:
        send_message(f'Сервер вернул ошибку: {error}')
    try:
        return homework_statuses.json()
    except json.JSONDecodeError:
        send_message('Сервер вернул невалидный json')


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарём')

    if 'homeworks' not in response:
        raise KeyError(f'Ключ "homeworks" не найден в {response}')

    if not isinstance(response['homeworks'], list):
        raise TypeError('В ключе "homeworks" нет списка')

    homeworks = response.get('homeworks')
    if not homeworks:
        raise KeyError('В ключе "homeworks" нет значений')

    return homeworks


def parse_status(homework):
    """извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутсвует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутсвует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.StatusException(
            f'Неизвестный статус работы: {homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical("Отсутствие обязательных переменных окружения")
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    error_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                message = 'Статус домашки не изменился'
                send_message(bot, message)
            if message != error_message:
                send_message(bot, message)
                error_message = message
            else:
                logging.info('Статус не изменился')

        except ConnectionError:
            pass
        except Exception as error:
            error_message = error
            logging.error(f"Бот столкнулся с ошибкой {error_message}")
        except telegram.error.TelegramError as error:
            error_message = error
            logging.error(f"Ошибка {error_message}")
        except requests.RequestException as error:
            error_message = error
            logging.error(f'Сервер вернул ошибку: {error_message}')
        except json.JSONDecodeError:
            logging.error('Сервер вернул невалидный json')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
