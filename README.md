# Network Utilization Monitor (SDN + Mininet + Ryu)

## Problem Statement
Design an SDN-based bandwidth monitoring system that collects byte counters from OpenFlow switches, estimates per-port bandwidth usage, and displays live utilization every 5 seconds.

## Topology
- 3 hosts: h1(10.0.0.1), h2(10.0.0.2), h3(10.0.0.3)
- 1 OVS switch: s1
- Remote Ryu controller (OpenFlow 1.3)

## Setup & Installation

### Prerequisites
sudo apt install mininet iperf wireshark -y
sudo pip3 install ryu eventlet==0.30.2

### Run

Terminal 1 - Start Ryu Controller:
source ~/ryuenv/bin/activate
ryu-manager monitor_controller.py

Terminal 2 - Start Mininet:
sudo python3 topology.py

## Test Scenarios

### Scenario 1 - Low vs High Utilization
mininet> h1 iperf -s &
mininet> h2 iperf -c 10.0.0.1 -t 30
Observe utilization jump from 0% to ~96% in Terminal 1.

### Scenario 2 - Link Failure and Recovery
mininet> link s1 h2 down
mininet> pingall
mininet> link s1 h2 up
mininet> pingall

## Expected Output
- Utilization table printed every 5 seconds
- Flow rules visible via: sudo ovs-ofctl dump-flows s1
- iperf throughput ~9.56 Mbits/sec on 10Mbps link

## References
- https://mininet.org/overview/
- https://ryu.readthedocs.io/
- https://opennetworking.org/sdn-resources/openflow/
