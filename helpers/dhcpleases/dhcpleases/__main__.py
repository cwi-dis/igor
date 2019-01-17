from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
import argparse
import time
import json

from .api import parse_leases_file, select_active_leases, test_pingable, test_arp, filter_keys, timestamp_now, DatetimeEncoder

def main():
    parser = argparse.ArgumentParser("Show active DHCP leases")
    parser.add_argument("-f", "--file", help="Alternative dhcpd.leases file", default='/var/lib/dhcp/dhcpd.leases')
    parser.add_argument("--json", action="store_true", help="Output information as JSON data")
    parser.add_argument("--wrap", action="store_true", help="Wrap JSON list into a dictionary for easy conversion to XML")
    parser.add_argument("-p", "--ping", action="store_true", help="Ping hosts to test liveness")
    parser.add_argument("-A", "--arp", action="store_true", help="Use ARP cache to test liveness")
    parser.add_argument("-a", "--inactive", action="store_true", help="Include also inactive leases")
    parser.add_argument("-i", "--include", action="append", metavar="F", help="Include field F in output (default: include all)", default=[])
    
    args = parser.parse_args()
    
    myfile = open(args.file, 'r')
    leases = parse_leases_file(myfile)
    myfile.close()

    now = timestamp_now()
    if args.inactive:
        report_dataset = []
        for l in leases.values():
            report_dataset += l
    else:
        report_dataset = select_active_leases(leases, now)

    if args.ping:
        report_dataset = test_pingable(report_dataset)
        
    if args.arp:
        report_dataset = test_arp(report_dataset)
        
    if args.include:
        report_dataset = filter_keys(report_dataset, args.include)
        
    if args.json:
        if args.wrap:
            report_dataset = {"lease" : report_dataset, "lastActivity" : time.time() }
        print(json.dumps(report_dataset, cls=DatetimeEncoder))
    else:

        print('+------------------------------------------------------------------------------')
        print('| DHCPD ACTIVE LEASES REPORT')
        print('+-----------------+-------------------+----------------------+-----------------')
        print('| IP Address      | MAC Address       | Expires (days,H:M:S) | Client Hostname ')
        print('+-----------------+-------------------+----------------------+-----------------')

        for lease in report_dataset:
                print('| ' + format(lease['ip-address'], '<15') + ' | ' + \
                        format(lease['hardware'], '<17') + ' | ' + \
                        format(str((lease['ends'] - now) if lease['ends'] != 'never' else 'never'), '>20') + ' | ' + \
                        lease['client-hostname'])

        print('+-----------------+-------------------+----------------------+-----------------')
        print('| Total Active Leases: ' + str(len(report_dataset)))
        print('| Report generated (UTC): ' + str(now))
        print('+------------------------------------------------------------------------------')

if __name__ == '__main__':
    main()
    
