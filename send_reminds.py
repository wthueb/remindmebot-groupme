import json
import logging
import logging.config
import sqlite3
import time

import requests

import config


conn = sqlite3.connect('reminds.db')
c = conn.cursor()

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
            'filename': 'log/remindmebot.log',
            'maxBytes': 2*1024*1024, # 2 MiB
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

logger = logging.getLogger('remindmebot')


def check_for_reminds() -> (list, time.struct_time):
    curtime = time.time()
    
    c.execute('SELECT * FROM reminds WHERE date <= ?', (curtime,))

    rows = c.fetchall()

    if rows:
        logger.info(f'we have {len(reminds)} to send')
        logger.debug(f'reminds: {rows}')

        return rows, curtime

    return None, None


def send_message(message, attachments=None) -> None:
    headers = {'content-type': 'application/json'}
    payload = {'text': message, 'bot_id': config.BOT_ID}

    if attachments:
        payload['attachments'] = attachments

    logger.info('sending reminds...')
    logger.debug(f'payload: {payload}')

    r = requests.post('https://api.groupme.com/v3/bots/post',
            headers=headers, data=json.dumps(payload))

    logger.info(f'sending message: {message}')
    logger.info(f'http response: {r.status_code}')


def send_reminds(reminds) -> None:
    for row in reminds:
        orig_msg, uid, name, created_at, attachments, date = row

        created_at = time.strftime('%x %-I:%M %p', time.localtime(created_at))

        msg = f'@{name}, you requested this reminder on {created_at}\nthe message: {orig_msg}'

        new_attachments = []

        if attachments:
            attachments = json.loads(attachments)

            for d in attachments:
                if d['type'] == 'mentions':
                    # adjust locations of original mentions
                    loci = d['loci']

                    new_loci = []

                    for loc in loci:
                        new_loc = []

                        for pos in loc:
                            new_loc.append(pos + len(msg) - len(orig_msg))

                        new_loci.append(new_loc)

                    d['loci'] = new_loci

                    # add mention of user asked to be reminded
                    d['user_ids'].append(uid)
                    d['loci'].append([0, len(name) + 1])

                new_attachments.append(d)

        if not new_attachments:
            new_attachments.append({'type': 'mentions', 'user_ids': [uid],
                                    'loci': [[0, len(name) + 1]]})

        send_message(msg, new_attachments)


def remove_from_db(updated_to) -> None:
    logger.debug(f'deleted reminds in database up to {updated_to}')

    c.execute('DELETE FROM reminds WHERE date <= ?', (updated_to,))
    
    conn.commit()


def main() -> None:
    logger.info('bot started, continually checking for reminds to send every 5 seconds...')

    while True:
        reminds, updated_to = check_for_reminds()

        if reminds:
            send_reminds(reminds)
            remove_from_db(updated_to)

        time.sleep(5)


if __name__ == '__main__':
    main()
