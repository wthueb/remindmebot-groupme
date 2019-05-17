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


def send_message(message, attachments=None) -> None:
    headers = {'content-type': 'application/json'}
    payload = {'text': message, 'bot_id': secret.bot_id}

    if attachments:
        payload['attachments'] = attachments

    r = requests.post('https://api.groupme.com/v3/bots/post',
            headers=headers, data=json.dumps(payload))

    logging.info('sending message: {}'.format(message))
    logging.info('http response: {}'.format(r.status_code))


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
