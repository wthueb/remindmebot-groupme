import json
import logging
import logging.config
import sqlite3
import time

from flask import Flask, request
import parsedatetime.parsedatetime as pdt


app = Flask(__name__)

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'brief': {
            'format': '%(asctime)s: %(message)s'
        },

        'precise': {
            'format': '%(asctime)s %(name)-15s %(levelname)-7s %(message)s'
        }
    },

    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'level': 'INFO',
            'formatter': 'brief'
        },

        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'log/webhook.log',
            'maxBytes': 2*1024*1024,  # 2 MiB
            'backupCount': 50,
            'level': 'DEBUG',
            'formatter': 'precise'
        }
    },

    'root': {
        'level': 'DEBUG',
        'handlers': ['stdout', 'file']
    }
})

logger = logging.getLogger('webhook')


def add_to_db(message, uid, name, created_at, attachments, date) -> None:
    logger.info(f'adding "{message}" from {name} to database')

    conn = sqlite3.connect('reminds.db')

    c = conn.cursor()

    if attachments is None:
        c.execute('INSERT INTO reminds VALUES (?, ?, ?, ?, NULL, ?)',
                  (message, uid, name, created_at, date))
    else:
        c.execute('INSERT INTO reminds VALUES (?, ?, ?, ?, ?, ?)',
                  (message, uid, name, created_at, attachments, date))

    conn.commit()

    conn.close()


def parse_message(message, uid, name, created_at, attachments) -> None:
    logger.debug(f'parsing message')

    temp = message.replace('-', '/')

    cal = pdt.Calendar()

    curtime = time.localtime(created_at)

    time_struct, status = cal.parse(temp, curtime)

    if status == 0:
        time_struct = cal.parse('1 day', curtime)

        logger.debug(f"couldn't find delay time, defaulting to {time_struct - curtime}")
    else:
        logger.debug('found delay of {time_struct - curtime}')

    logger.debug('will send the reminder at: {time_struct}')

    epoch = time.mktime(time_struct)

    add_to_db(message, uid, name, created_at, attachments, epoch)


@app.route('/api/remindmebot-callback', methods=['POST'])
def new_message() -> str:
    r = request.get_json()

    message = r['text']
    name = r['name']

    if (('!remindme' in message.lower() or 'remindme!' in message.lower()) and
            name != 'remindmebot'):
        logger.info(f'got a new message from {name} to add to the database')

        attachments = str(json.dumps(r['attachments'])) if 'attachments' in r else None

        parse_message(message, r['user_id'], name, r['created_at'], attachments)

    return ''


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
