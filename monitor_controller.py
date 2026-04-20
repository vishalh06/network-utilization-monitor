#!/usr/bin/env python3
"""
Network Utilization Monitor - Ryu Controller
- Handles packet_in events (learning switch)
- Installs OpenFlow flow rules
- Polls port statistics every 5 seconds
- Calculates and displays bandwidth utilization
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.lib import hub
import time

POLL_INTERVAL = 5
LINK_CAPACITY = 10e6  # 10 Mbps in bits/sec

class NetworkMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(NetworkMonitor, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.port_stats_prev = {}
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, priority=0, match=match, actions=actions)
        self.logger.info("Switch %s connected", datapath.id)

    def _add_flow(self, datapath, priority, match, actions,
                  idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority,
            match=match, instructions=inst,
            idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port, eth_dst=dst, eth_src=src)
            self._add_flow(datapath, priority=1, match=match,
                           actions=actions, idle_timeout=30,
                           hard_timeout=120)
            self.logger.info("Flow installed: %s → port %s on sw %s",
                             dst, out_port, dpid)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None)
        datapath.send_msg(out)

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_port_stats(dp)
            hub.sleep(POLL_INTERVAL)

    def _request_port_stats(self, datapath):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        now = time.time()

        self.port_stats_prev.setdefault(dpid, {})

        print(f"\n{'='*60}")
        print(f"  NETWORK UTILIZATION — Switch {dpid} — {time.strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"  {'Port':<6} {'TX Bytes':>12} {'RX Bytes':>12} "
              f"{'TX Mbps':>10} {'RX Mbps':>10} {'Util%':>8}")
        print(f"  {'-'*58}")

        for stat in sorted(body, key=lambda s: s.port_no):
            port = stat.port_no
            if port > 65000:
                continue

            tx_bytes = stat.tx_bytes
            rx_bytes = stat.rx_bytes

            if port in self.port_stats_prev[dpid]:
                prev = self.port_stats_prev[dpid][port]
                dt = now - prev['time']
                if dt > 0:
                    tx_bps = (tx_bytes - prev['tx']) * 8 / dt
                    rx_bps = (rx_bytes - prev['rx']) * 8 / dt
                    tx_mbps = tx_bps / 1e6
                    rx_mbps = rx_bps / 1e6
                    util = min((max(tx_bps, rx_bps) / LINK_CAPACITY) * 100, 100)
                    print(f"  {port:<6} {tx_bytes:>12} {rx_bytes:>12} "
                          f"{tx_mbps:>10.3f} {rx_mbps:>10.3f} {util:>7.1f}%")
                else:
                    print(f"  {port:<6} {tx_bytes:>12} {rx_bytes:>12}"
                          f"{'(calculating)':>32}")
            else:
                print(f"  {port:<6} {tx_bytes:>12} {rx_bytes:>12}"
                      f"{'(first sample)':>32}")

            self.port_stats_prev[dpid][port] = {
                'tx': tx_bytes, 'rx': rx_bytes, 'time': now}

        print(f"{'='*60}\n")
