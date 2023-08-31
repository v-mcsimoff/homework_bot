### Homework Telegram bot

```
Telegram bot for tracking the status of homework checking on Yandex.Praktikum.
It sends messages when the status is changed - review started, there are remarks, passed.
```

### Technologies:
- Python 3.9
- python-dotenv 0.19.0
- python-telegram-bot 13.7

### How to launch the project:

Clone the repository and access it in the terminal:

```
git clone git@github.com:v-mcsimoff/homework_bot.git
```

```
cd homework_bot
```

Create and activate a virtual environment:

```
python -m venv env
```

```
source env/bin/activate
```

Install dependencies from requirements.txt:

```
python -m pip install --upgrade pip
```

```
pip install -r requirements.txt
```

Save the necessary keys to the environment variables (.env file):
- Yandex.Practicum profile token
- Telegram bot token
- Telegram ID


Launch the project:

```
python homework.py
```
