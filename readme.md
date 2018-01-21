# An implementation for the Raft log consensus algorithm in Python 3

To run the test which demonstrates the algorithm:
* Create new Python 3.6 virtual environment
* Run `pip install -r requirements.txt` to install dependencies.
* Run `./run_test.sh` to start 5 servers and execute the client test which send a couple of log entries to the Raft cluster.

If the execution is successful then the output shold look like:
```
Server 5002 - Started server 5002
Server 5001 - Started server 5001
Server 5004 - Started server 5004
Server 5003 - Started server 5003
Server 5005 - Started server 5005
Client - Randomly selected '5001' as a leader.
Client - Making append entries request to '5001.'
Server 5001 - Redirecting request a client to None.
Client - Failed to make successful append entries request to '5001' because the leader is not elected yet.
Client - Sleeping for 2 seconds.
Server 5001 - Starting elections.
Server 5001 - Requesting vote from '5002''.
Server 5001 - Got a vote from 5002, total 2 votes. Need at least 3 votes to win.
Server 5001 - Requesting vote from '5003''.
Server 5001 - Got a vote from 5003, total 3 votes. Need at least 3 votes to win.
Server 5001 - Elected leader
Client - Randomly selected '5005' as a leader.
Client - Making append entries request to '5005.'
Server 5005 - Redirecting request a client to 5001.
Client - 5005 indicated that 5001 is the leader.
Client - Making append entries request to '5001.'
Server 5001 - Appending the entry to the leader log.
Server 5001 - Requesting 5002 to append entry after 0:0.
Server 5002 - Appending item from 5001.
Server 5001 - The 5002 is committed at 1:1.
Server 5001 - Requesting 5003 to append entry after 0:0.
Server 5003 - Appending item from 5001.
Server 5001 - The 5003 is committed at 1:1.
Server 5001 - Set the commit_index to new value 1.
Server 5001 - Committed the 1:1 entry on the majority 3 of servers.
Client - Made successful append entries request to '5001'.
Client - Making append entries request to '5001.'
Server 5001 - Appending the entry to the leader log.
Server 5001 - Requesting 5002 to append entry after 1:1.
Server 5002 - Appending item from 5001.
Server 5001 - The 5002 is committed at 1:2.
Server 5001 - Requesting 5003 to append entry after 1:1.
Server 5003 - Appending item from 5001.
Server 5001 - The 5003 is committed at 1:2.
Server 5001 - Set the commit_index to new value 2.
Server 5001 - Committed the 1:2 entry on the majority 3 of servers.
Client - Made successful append entries request to '5001'.
Server 5001 - Requesting 5004 to append entry after 0:0.
Server 5004 - Appending item from 5001.
Server 5001 - The 5004 is committed at 1:1.
Server 5001 - Requesting 5004 to append entry after 1:1.
Server 5004 - Appending item from 5001.
Server 5001 - The 5004 is committed at 1:2.
Server 5001 - Requesting 5005 to append entry after 0:0.
Server 5005 - Appending item from 5001.
Server 5001 - The 5005 is committed at 1:1.
Server 5001 - Requesting 5005 to append entry after 1:1.
Server 5005 - Appending item from 5001.
Server 5001 - The 5005 is committed at 1:2.
```

The servers are started as background bash jobs. To stop them either kill all background jobs or execute `killall python`.


The project structure:
server.py - A protocol agnostic implementation of the Raft server.
client.py - A protocol agnostic implementation of the Raft client.
timeouts.py - Timeouts constant used by the Raft clients and servers.
log.py - An implementation of the Raft log. Which is used by the Raft server.
http_raft.py - An implementation of the Raft server transport as Flask HTTP server, and the Raft client as an HTTP client.
client_test.py - A test which initializes a Raft client and send a couple of messages to the Raft cluster.
servers - A list of ports on which the Raft servers should start. It should match the list of servers started by run_tests.sh.
run_tests.sh - Starts a Raft cluster and runs a client test.
requirements.txt - A list of Python project dependencies.

