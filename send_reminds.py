import json
import logging
import sqlite3
import time

import requests

import secret


conn = sqlite3.connect('reminds.db')
c = conn.cursor()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def check_for_reminds() -> list:
    curtime = time.time()
    
    c.execute('SELECT * FROM reminds WHERE date <= ?', (curtime,))

    rows = c.fetchall()

    return rows, curtime


def find_nth(string, search, n) -> int:
    start = string.find(search)

    while start >= 0 and n > 1:
        start = string.find(search, start + len(search))
        n -= 1

    return start


def send_message(message, mentions=None) -> None:
    headers = {'content-type': 'application/json'}
    payload = {'text': message, 'bot_id': secret.bot_id}

    if mentions is not None:
        for i in range(len(mentions)):
            mention = mentions[i]

            if 'attachments' not in payload:
                payload['attachments'] = [{'type': 'mentions',
                    'user_ids': [mention[0]], 'loci': [(message.find('@'), len(mention[1]) + 1)]}]
            else:
                payload['attachments'][0]['user_ids'].append(mention[0])
                payload['attachments'][0]['loci'].extend(find_nth(message, '@', i + 1),
                        len(mention[1]) + 1)

    r = requests.post('https://api.groupme.com/v3/bots/post',
            headers=headers, data=json.dumps(payload))

    logging.info('sending message: {}'.format(message))
    logging.info('http response: {}'.format(r.status_code))


def send_reminds(reminds) -> None:
    for row in reminds:
        orig_msg, uid, name, created_at, date = row
        
        created_at_text = time.strftime('%x %-I:%M %p', time.localtime(created_at))

        send_message(('@{}, you requested this reminder on {}\nthe message: {}').format(
            name, created_at_text, orig_msg), mentions=((uid, name),))


def remove_from_db(reminds, updated_to) -> None:
    c.execute('DELETE FROM reminds WHERE date <= ?', (updated_to,))
    
    conn.commit()


def main() -> None:
    while True:
        reminds, updated_to = check_for_reminds()
        send_reminds(reminds)
        remove_from_db(reminds, updated_to)

        time.sleep(5)


if __name__ == '__main__':
    main()
