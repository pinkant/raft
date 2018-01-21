import random
import time
import timeouts


class Client:
    """Implements the client logic for the Raft consensus algorithms."""

    def __init__(self, servers, append_entries_transport, logger):
        """
        Initializes the client object.

        A server implementation is protocol agnostic. A list of callbacks
        for transporting messages has to be provided by the consumer of
        this class.

        :param servers: The list of Raft server IDs. The format of IDs
                        has to be understood by the transport callbacks
                        and has to provide human readable __str__ implementation,
                        so IDs could be used in the log messages.
                        This class does not depend on any particular format.
        :param append_entries_transport: The transport which implements the append entry request
                                         to the servers.

        :param logger: The logger object for emitting diagnostic info.
        """
        self.servers = servers
        self.append_entries_transport = append_entries_transport
        self.logger = logger
        self.leader = None

    def append_entries(self, entries):
        """
        Send entries to the Raft server.

        Returns when the entries are successfully committed.
        """
        while True:
            if not self.leader:
                self.leader = random.choice(self.servers)
                self.logger.info(f"Randomly selected '{self.leader}' as a leader.")

            self.logger.info(f"Making append entries request to '{self.leader}.'")
            result = self.append_entries_transport(self.leader, entries, timeouts.REQUEST, self.logger)

            if result and result['success']:
                self.logger.info(f"Made successful append entries request to '{self.leader}'.")
                return

            if not result:
                self.logger.info(f"Failed to make successful append entries request to '{self.leader}' "
                                 f"because of connectivity issues.")
                timeout = timeouts.REQUEST
            elif not result.get('leader'):
                self.logger.info(f"Failed to make successful append entries request to '{self.leader}' "
                                 f"because the leader is not elected yet.")
                self.leader = None
                timeout = timeouts.REQUEST
            else:
                self.logger.info(f"{self.leader} indicated that {result['leader']} is the leader.")
                self.leader = result['leader']
                timeout = 0

            if timeout:
                self.logger.info(f"Sleeping for {timeout} seconds.")
                time.sleep(timeout)
