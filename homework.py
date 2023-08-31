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
    'approved': 'Work checked: the reviewer liked everything. Yay!',
    'reviewing': 'Review has been started by the reviewer.',
    'rejected': 'Work checked: the reviewer has comments.'
}


def check_tokens():
    """Checks if environment variables are available."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Sends a message to the Telegram chat."""
    try:
        logging.info('Sending the message')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('The message has been sent')
    except telegram.error.TelegramError as error:
        error_message = f'Error while sending the message: {error}'
        logging.error(f"Error {error_message}")
        raise exceptions.SendMessageException(error_message)


def get_api_answer(timestamp):
    """Makes a request to a single endpoint of the API service."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=headers, params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise exceptions.GetAPIException('Request status is not 200')
    except requests.RequestException as error:
        send_message(f'The server returned the error: {error}')
    try:
        return homework_statuses.json()
    except json.JSONDecodeError:
        send_message('The server returned invalid json')


def check_response(response):
    """Checks the API response for compliance with the documentation."""
    if not isinstance(response, dict):
        raise TypeError('The response from API is not a dictionary')

    if 'homeworks' not in response:
        raise KeyError(f'The key "homeworks" has not been found in {response}')

    if not isinstance(response['homeworks'], list):
        raise TypeError('There's no list in the "homeworks" key')

    homeworks = response.get('homeworks')
    if not homeworks:
        raise KeyError('There are no values in the "homeworks" key')

    return homeworks


def parse_status(homework):
    """Retrieves the status of homework."""
    if 'homework_name' not in homework:
        raise KeyError('Missing "homework_name" key in API response')
    if 'status' not in homework:
        raise KeyError('Missing "status" key in API response')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.StatusException(
            f'Unknown operation status: {homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'The status of the work "{homework_name}" review has changed. {verdict}'


def main():
    """General logic of the bot's operation."""
    if not check_tokens():
        logging.critical("Lack of mandatory environment variables")
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
                message = 'No change in the status of the homework'
                send_message(bot, message)
            if message != error_message:
                send_message(bot, message)
                error_message = message
            else:
                logging.info('No change in status')

        except ConnectionError:
            pass
        except Exception as error:
            error_message = error
            logging.error(f"The bot faced an error {error_message}")
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s',
        handlers=[logging.FileHandler('main.log', 'w', encoding='utf-8'),
                  logging.StreamHandler(sys.stdout)]
    )
    main()
