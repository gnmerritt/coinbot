import sys
from flask import Flask, jsonify, request
app = Flask(__name__)

import config
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
    commands = [w for w in text.split() if w in ALLOWED_ACTIONS]

    main(parsed, commands)
    return jsonify({"success": True, "commands": commands})


if __name__ == "__main__":
    config_file = sys.argv[1]
    parsed = config.read_config(config_file)
    app.run(host='0.0.0.0', port=80)
