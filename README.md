This project is an implementation of a reliable data transfer(RDT) protocal over UDP with congestion control

Note:
1. The program is built with Python 3.8.3 
2. The program is tested on ubuntu2004-0AB.student.cs.uwaterloo.ca as host 1, ubuntu2004-0CD.student.cs.uwaterloo.ca as host 2 and ubuntu2004-0EF as host 3, where AB, CD, EF is any tow digit number
3. Delete *.log file and output file everytime before running the programming (rm *.log)

Usage:
1. Ge the 3 random port "port1", "port2", "port3" and a random guessing "port4":
```
comm -23 <(seq 1024 65535 | sort) <(ss -tan | awk '{print $4}' | cut -d':' -f2 | grep "[0-9]\{1,5\}" | sort -u) | shuf | 
head -n 3
```

2. Initiate the nEmulator, with chosen <maximum_delay>, <packet_discard_probability> and <verbose-mode> (either 0 or 1)
```
python3 network_emulator.py <port1> <host2> <port4> <port3> <host3> <port2> <maximum_delay> <packet_discard_probability> <verbose-mode>
```

3. Initiate the receiver with output file name
```
python3 receiver.py <host1> <port3> <port4> <output file name>
```

4. Initiate the sender with fetch file name with timeout interval in miliseconds
```
 python3 sender.py <host1> <port1> <port2> <timeout interval> <fetch file name>
```