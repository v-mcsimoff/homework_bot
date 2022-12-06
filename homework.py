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
        raise exceptions.APIResponseException(error_message)
    return homework_list


def parse_status(homework):
    """извлекает статус домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        error_message = f'В словаре нет ключа homework_name {error}'
        logging.error(error_message)
        raise KeyError(error_message)
    try:
        homework_status = homework['status']
    except KeyError as error:
        error_message = f'В словаре нет ключа status {error}'
        logging.error(error_message)
        raise KeyError(error_message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    if verdict is None:
        error_message = 'Отсутствует сообщение о статусе проверки'
        logging.error(error_message)
        raise exceptions.StatusException(error_message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler('program.log'),
            logging.StreamHandler(sys.stdout)
        ],
    )

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            new_homework = get_api_answer(timestamp)
            if new_homework.get('homeworks'):
                send_message(parse_status(
                    new_homework.get('homeworks')[0]),
                    bot
                )
            timestamp = new_homework.get('current_date')
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(f'Ошибка бота: {error}')
            send_message(f'{message} {error}', bot)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
