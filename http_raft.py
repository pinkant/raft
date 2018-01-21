from argparse import ArgumentParser
from flask import Flask, request, jsonify
import logging
import requests
import server

HOST = 'http://localhost:'
CLIENT_APPEND_ENTRIES_URL = '/client_append_entries'
APPEND_ENTRIES_URL = '/append_entries'
REQUEST_VOTE_URL = '/request_vote'

logging.getLogger('werkzeug').setLevel(logging.CRITICAL)


def client_make_request(route, server_id, request_body, timeout, action_name, logger):
    url = HOST + server_id + route
    try:
        response = requests.post(url=url, json=request_body, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (ConnectionRefusedError, requests.urllib3.exceptions.MaxRetryError, requests.ConnectionError):
        logger.error(action_name + ' cannot connect')
    except requests.RequestException:
        logger.exception(action_name + ' request failed')


def client_append_entries(server_id, entries, timeout, logger):
    return client_make_request(CLIENT_APPEND_ENTRIES_URL, server_id, entries,
                               timeout, 'Append entries', logger)


def append_entries(server_id, entries, timeout, logger):
    return client_make_request(APPEND_ENTRIES_URL, server_id, entries,
                               timeout, 'Append entries', logger)


def request_vote(server_id, vote_request, timeout, logger):
    return client_make_request(REQUEST_VOTE_URL, server_id, vote_request,
                               timeout, 'Vote', logger)


app = Flask(__name__)


@app.route(APPEND_ENTRIES_URL, methods=['POST'])
def append_entries_handler():
    global raft_server
    return jsonify(raft_server.handle_append_entry_request(request.get_json()))


@app.route(REQUEST_VOTE_URL, methods=['POST'])
def request_vote_handler():
    global raft_server
    response = raft_server.handle_vote_request(request.get_json())
    return jsonify(response)


@app.route(CLIENT_APPEND_ENTRIES_URL, methods=['POST'])
def client_append_entries_handler():
    global raft_server
    return jsonify(raft_server.handle_client_append_entry_request(request.get_json()))


def load_servers():
    with open('servers') as servers_file:
        return [line.strip() for line in servers_file.readlines()]


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("server_index", help="The order number of this server in the list (1 based).", type=int)
    args = parser.parse_args()

    servers = load_servers()

    server_logger = logging.getLogger('Server ' + servers[args.server_index - 1])
    server_logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    server_logger.addHandler(handler)

    raft_server = server.Server(servers, args.server_index - 1, append_entries, request_vote, server_logger)

    app.run(
        host='localhost',
        port=int(raft_server.id)
    )
