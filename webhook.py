import sqlite3
import time

from flask import Flask, request
import parsedatetime.parsedatetime as pdt


app = Flask(__name__)


def add_to_db(message, uid, name, created_at, date) -> None:
    conn = sqlite3.connect('reminds.db')

    c = conn.cursor()
    
    c.execute('INSERT INTO reminds VALUES (?, ?, ?, ?, ?)', (message, uid, name, created_at, date))
    
    conn.commit()

    conn.close()


def parse_message(message, uid, name, created_at) -> None:
    temp = message.replace('-', '/')
    
    cal = pdt.Calendar()

    time_struct, status = cal.parse(temp, time.localtime(created_at))

    if status == 0:
        new_time = cal.parse('1 day', time.localtime(created_at))

    epoch = time.mktime(time_struct)

    add_to_db(message, uid, name, created_at, epoch)


@app.route('/api/remindmebot-callback', methods=['POST'])
def new_message() -> str:
    r = request.get_json()

    message = r['text']
    name = r['name']

    if (('!remindme' in message.lower() or 'remindme!' in message.lower()) and 
            name != 'remindmebot'):
        parse_message(message, r['user_id'], name, r['created_at'])

    return ''


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
