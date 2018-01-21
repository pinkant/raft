#!/usr/bin/env bash
python http_raft.py 1 &
python http_raft.py 2 &
python http_raft.py 3 &
python http_raft.py 4 &
python http_raft.py 5 &
python client_test.py &
