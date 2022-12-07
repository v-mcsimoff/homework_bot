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


def check_tokens():
    """проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        error_message = f'Ошибка при отправке сообщения: {error}'
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
    except requests.exceptions.RequestException as error:
        logging.error(f'Сервер вернул ошибку: {error}')
        send_message(f'Сервер вернул ошибку: {error}')
    try:
        return homework_statuses.json()
    except json.JSONDecodeError:
        logging.error('Сервер вернул невалидный json')
        send_message('Сервер вернул невалидный json')


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    try:
        homework_list = response['homeworks']
    except KeyError as error:
        error_message = f'В словаре нет ключа homeworks {error}'
        logging.error(error_message)
        raise KeyError(error_message)
    if not homework_list:
        error_message = 'В ответе API нет списка домашек'
        logging.error(error_message)
        raise exceptions.APIResponseException(error_message)
    if len(homework_list) == 0:
        error_message = 'Вы ничего не отправляли на ревью'
        logging.error(error_message)
        raise exceptions.APIResponseException(error_message)
    if not isinstance(homework_list, list):
        error_message = 'В ответе API домашки выводятся не списком'
        logging.error(error_message)
        raise TypeError(error_message)
    return homework_list


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
    timestamp = int(time.time())
    status = ''
    error_message = ''
    if not check_tokens():
        logging.critical('Отсутствуют одна или несколько переменных окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != status:
                logging.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
                send_message(bot, message)
                status = message
        except telegram.error.TelegramError as error:
            logging.error(error)
        except Exception as error:
            logging.error(error)
            message_t = str(error)
            if message_t != error_message:
                send_message(bot, message_t)
                error_message = message_t
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
