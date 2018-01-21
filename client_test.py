from client import Client
import http_raft
import logging

logger = logging.getLogger('Client')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)
client = Client(http_raft.load_servers(), http_raft.client_append_entries, logger)

client.append_entries({'a': 1})
client.append_entries({'a': 2})
