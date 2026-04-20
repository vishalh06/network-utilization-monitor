#!/usr/bin/env python3
"""
Network Utilization Monitor - Custom Mininet Topology
3 hosts connected to 1 switch
"""
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.link import TCLink

class MonitorTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        self.addLink(h1, s1, bw=10)
        self.addLink(h2, s1, bw=10)
        self.addLink(h3, s1, bw=10)

def run():
    topo = MonitorTopo()
    net = Mininet(
        topo=topo,
        controller=RemoteController('c0', ip='127.0.0.1', port=6633),
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    net.start()
    print("=== Network Utilization Monitor Topology Started ===")
    print("Hosts: h1(10.0.0.1), h2(10.0.0.2), h3(10.0.0.3)")
    print("Run 'pingall' to verify connectivity")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
