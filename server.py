from enum import Enum
from log import Log
import random
from threading import Thread, Condition
import timeouts


class Role(Enum):
    FOLLOWER = 1
    LEADER = 2
    CANDIDATE = 3


class Server:
    """ The Raft server implementation. """
    def __init__(self, servers, server_index, append_entries_transport, request_vote_transport, logger):
        """
        Initializes the server object.

        A client implementation is protocol agnostic. A list of callbacks
        for transporting messages has to be provided by the consumer of
        this class.

        :param servers: The list of Raft server IDs. The format of IDs
                        has to be understood by the transport callbacks
                        and has to provide human readable __str__ implementation,
                        so IDs could be used in the log messages.
                        This class does not depend on any particular format.
        :param server_index: 0-based index of the server which will be served by the instance.
        :param append_entries_transport: The transport which will implement append entries request
                                         to followers.
        :param request_vote_transport: The transport which will implement vote request to other servers.
        :param logger: The logger object for emitting diagnostic info.
        """
        self.id = servers[server_index]
        self.servers = servers
        self.majority = len(servers) // 2 + 1
        del self.servers[server_index]
        logger.info(f"Started server {self.id}")

        self.append_entries_transport = append_entries_transport
        self.request_vote_transport = request_vote_transport

        self.logger = logger

        self.role = Role.FOLLOWER
        self.talked_to_leader = False

        self.current_term = 0
        self.voted_for = None
        self.log = Log(logger)

        self.leader_id = None

        self.commit_index = 0
        self.last_applied = 0

        self.followers_next_indexes = {}
        self.followers_match_indexes = {}

        # Start threads after all data structures are set up.
        # ToDo protect data from concurrent updates from multiple threads.

        # Set up the election thread before tracking thread,
        # because the tracking thread can request votes immediately.
        self.election_lock = Condition()
        self.election_thread = Thread(target=self.do_elections)
        self.election_thread.daemon = True
        self.election_thread.start()

        self.heartbeat_lock = Condition()
        self.heartbeat_thread = Thread(target=self.send_heartbeats_and_sync_up)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def handle_append_entry_request(self, request):
        """
        Handles append entry requests from other servers.

        (The method semantic and the message format is described in the Raft paper.)

        :param request: The request JSON.
        :return: The response JSON.
        """
        result = {
            'term': self.current_term,
            'success': False
        }
        if request['term'] < self.current_term:
            self.logger.info(f"Refusing append request from {request['leaderId']} because "
                             f"it has smaller term {request['term']} than the current term {self.current_term}.")
            return result

        self.role = Role.FOLLOWER
        self.talked_to_leader = True
        self.leader_id = request['leaderId']
        self.current_term = request['term']
        self.voted_for = None

        if not self.log.sync_at_item(request['prevLogIndex'], request['prevLogTerm']):
            self.logger.info(f"Refusing append request from {request['leaderId']} because "
                             f"it has conflicting log message")
            return result

        result['success'] = True

        if request['entry']:
            self.logger.info(f"Appending item from {request['leaderId']}.")
            self.log.append_item(request['term'], request['entry'])

        if request['leaderCommit'] > self.commit_index:
            self.commit_index = min(request['leaderCommit'], self.log.len())
        return result

    def handle_vote_request(self, request):
        """
        Handles vote requests from other servers.

        (The method semantic and the message format is described in the Raft paper.)

        :param request: The request JSON.
        :return: The response JSON.
        """
        result = {
            'term': self.current_term,
            'voteGranted': False
        }
        candidate_id = request['candidateId']
        if request['term'] < self.current_term:
            self.logger.info(f"Rejecting vote request from {candidate_id} because requested term "
                             f"{request['term']} is smaller than current term {self.current_term}.")
            return result

        if self.voted_for and self.voted_for != candidate_id:
            self.logger.info(f"Rejected vote request from {candidate_id} "
                             f"because already voted for {self.voted_for}.")
            return result

        candidate_last_log_term = request['lastLogTerm']
        candidate_last_log_index = request['lastLogIndex']
        last_term = self.log.get_item_term(self.log.len())
        if last_term > candidate_last_log_term:
            self.logger.info(f"Rejected vote request from {candidate_id} because its term "
                             f"{candidate_last_log_term} is smaller than the current last term "
                             f"{last_term}.")
            return result
        elif self.log.len() > candidate_last_log_index:
            self.logger.info(f"Rejected vote request from {candidate_id} because its last index "
                             f"{candidate_last_log_index} is smaller the length current index {self.log.len()}.")
            return result

        self.voted_for = candidate_id
        result['voteGranted'] = True
        return result

    def handle_client_append_entry_request(self, entry):
        """
        Handles client append requests.

        (The method semantic and the message format is described in the Raft paper.)

        :param entry: The entry JSON.
        :return: The response JSON.
        """
        if self.role != Role.LEADER:
            self.logger.info(f"Redirecting request a client to {self.leader_id}.")
            return {
                'success': False,
                'leader': self.leader_id
            }
        self.logger.info("Appending the entry to the leader log.")
        entry_index = self.log.append_item(self.current_term, entry)
        server_index = 0
        while True:
            # Wrap the server index to the first element if the index
            # was increased beyond the lest element.
            # This way the loop will keep going until enough servers will commit the entry.
            server_index = server_index % len(self.servers)
            server = self.servers[server_index]
            next_index = self.append_entry_to_follower(server)
            if self.role != Role.LEADER:
                self.logger.info(f"Lost leadership while waiting for response from {server}. "
                                 f"{self.leader_id} is now a leader.")
                return {
                    'success': False,
                    'leader': self.leader_id
                }
            if not next_index:
                # Move on to the next server because cannot connect.
                server_index += 1
                continue
            if entry_index >= next_index:
                # Keep trying to append results until enough elements synced.
                continue
            assert(entry_index < next_index)
            if self.commit_index == entry_index:
                self.logger.info(f"Committed the {self.current_term}:{entry_index} entry on the majority "
                                 f"{self.majority} of servers.")
                return {
                    'success': True,
                    'leader': self.leader_id
                }
            # Move on to the next server.
            server_index += 1

    def send_heartbeats_and_sync_up(self):
        """
        The entry point method for the thread which is responsible for
        sending heartbeats and updating follower servers.
        """
        while True:
            if self.role == Role.LEADER:
                for server in self.servers:
                    while True:
                        next_index = self.append_entry_to_follower(server)
                        if not next_index or next_index > self.log.len():
                            break
                # Poor man way to guaranty that the all heartbeats are finished in time.
                # ToDo Replace with parallel requests and add a timer which cancels them if they are not done in time.
                timeout = random.uniform(timeouts.MIN_VOTING / 4.0, timeouts.MIN_VOTING / 2.0)
            else:
                # If not a leader wait until woken up after winning an election.
                timeout = None
            with self.heartbeat_lock:
                self.heartbeat_lock.wait(timeout)

    def do_elections(self):
        """
        The entry method for the thread which is response for running the elections.
        """
        while True:
            with self.election_lock:
                timeout = random.uniform(timeouts.MIN_VOTING, timeouts.MAX_VOTING)
                self.election_lock.wait(timeout)

            if self.role == Role.LEADER:
                continue

            if self.talked_to_leader:
                self.talked_to_leader = None
                continue

            self.logger.info("Starting elections.")
            self.role = Role.CANDIDATE
            self.current_term += 1
            # Vote for itself.
            votes = 1
            for server in self.servers:
                self.logger.info(f"Requesting vote from '{server}''.")
                last_log_index = self.log.len()
                last_log_term = self.log.get_item_term(last_log_index)
                vote = self.request_vote_transport(
                    server,
                    {
                        'term': self.current_term,
                        'candidateId': self.id,
                        'lastLogIndex': last_log_index,
                        'lastLogTerm': last_log_term
                    },
                    # Poor man way to guaranty that the all votes are finished in time.
                    # ToDo Replace with parallel requests and add a timer which cancels them
                    # if they are not done in time.
                    timeouts.MIN_VOTING / len(self.servers),
                    self.logger
                )
                if not vote:
                    self.logger.info(f"'{server}' did not reply.")
                    continue

                self.check_response_term(vote)

                # Can happen because either the response had a higher term
                # or if the server got contacted by a newly elected leader.
                if self.role == Role.FOLLOWER:
                    self.logger.info(f"Canceling voting because {self.leader_id} became a leader.")
                    break

                if vote['voteGranted']:
                    votes += 1
                    self.logger.info(f"Got a vote from {server}, total {votes} votes. "
                                     f"Need at least {self.majority} votes to win.")

                if votes >= self.majority:
                    self.logger.info("Elected leader")
                    self.role = Role.LEADER
                    self.followers_next_indexes = dict(zip(self.servers, [self.log.len() + 1] * len(self.servers)))
                    self.followers_match_indexes = dict(zip(self.servers, [0] * len(self.servers)))
                    with self.heartbeat_lock:
                        self.heartbeat_lock.notify()
                    break

    def append_entry_to_follower(self, follower_server):
        """
        Sends the append entry request to the specified follower.

        It checks the term value of the response and resets
        the server to the follower mode if the response has
        a higher term.

        It updates the commit_index if the request resulted
        in enough followers to be updated to increase the value.

        :param follower_server: The ID of the follower server.
        :return: The next_index value for the follower server after
                 the append entry is executed. None if could not
                 connect to the follower.
        """
        next_index = self.followers_next_indexes[follower_server]
        prev_log_index = next_index - 1
        prev_log_term = self.log.get_item_term(prev_log_index)
        entry = self.log.get_item(next_index)
        if entry:
            # Do not emmit log messages for heartbeat to do not clutter the output.
            self.logger.info(f"Requesting {follower_server} to append entry after {prev_log_term}:{prev_log_index}.")
        result = self.append_entries_transport(
            follower_server,
            {
                'term': self.current_term,
                'leaderId': self.id,
                'prevLogIndex': prev_log_index,
                'prevLogTerm': prev_log_term,
                'entry': entry,
                'leaderCommit': self.commit_index
            },
            timeouts.REQUEST,
            self.logger
        )
        if not result:
            self.logger.inf(f"Could not deliver new entry to {follower_server}.")
            return None

        if not self.check_response_term(result):
            return None

        if not result['success']:
            self.followers_next_indexes[follower_server] -= 1
            assert(self.followers_next_indexes[follower_server] > 0)
        elif entry:
            self.followers_next_indexes[follower_server] += 1
            self.logger.info(f"The {follower_server} is committed at {self.current_term}:{next_index}.")
            self.followers_match_indexes[follower_server] = next_index
            # Calling this function after each request will guarantee
            # that the commit_index will increase without any delays.
            self.try_leader_commit(next_index)
        return self.followers_next_indexes[follower_server]

    def try_leader_commit(self, index):
        """
        Try to commit an element with the given index in the leader's log.

        :param index: The index of the log element to try to commit.
        :return: True if the element at the given index is committed, otherwise False.
        """
        if self.commit_index >= index:
            return True

        # Count itself
        committed_servers = 1
        for match_index in self.followers_match_indexes.values():
            committed_servers += match_index >= index
            if committed_servers >= self.majority:
                self.commit_index = index
                self.logger.info(f"Set the commit_index to new value {self.commit_index}.")
                return True

        return False

    def check_response_term(self, response):
        """
        Checks if the response from the server contains a bigger term than the server's
        current term.

        If the response term is more recent than the server's term then the server is
        switched to the follower mode.

        :param response: A response from one of the follower servers.
        :return: True if the server's term is up to date, otherwise False.
        """
        if response['term'] > self.current_term:
            self.logger.info(f"The response includes a bigger term {response['term']} "
                             f"than the current term {self.current_term}.")
            self.logger.info(f"Switching to the follower mode.")
            self.role = Role.FOLLOWER
            self.current_term = response['term']
            self.leader_id = None
            return False
        return True
