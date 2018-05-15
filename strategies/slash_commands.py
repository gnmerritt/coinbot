import sys
from threading import Thread
from flask import Flask, request
app = Flask(__name__)

import config
from slack import setup_loggers
from cron import main

ALLOWED_ACTIONS = set([
    'pull', 'account', 'strengths', 'data', 'tick', 'update'
])


@app.route('/slack', methods=['POST'])
def handle_slack():
    token = request.form.get('token')
    if token != parsed['slack']['token']:
        raise Exception("IllegalRequest")
    # user = request.form.get('user_name')
    text = request.form.get('text')
    if not text:
        return "No commands"
    commands = [w for w in text.split() if w in ALLOWED_ACTIONS]

    t = Thread(target=action_runner, args=(commands,))
    t.start()
    return "Ok"


def action_runner(actions):
    main(parsed, actions)


if __name__ == "__main__":
    config_file = sys.argv[1]
    parsed = config.read_config(config_file)
    setup_loggers(parsed['slack'])
    app.run(host='0.0.0.0', port=5000)
