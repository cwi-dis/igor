import datetime
import time
import bisect
import json
import sys
import subprocess

def parse_timestamp(raw_str):
        tokens = raw_str.split()

        if len(tokens) == 1:
                if tokens[0].lower() == 'never':
                        return 'never';

                else:
                        raise Exception('Parse error in timestamp')

        elif len(tokens) == 3:
                return datetime.datetime.strptime(' '.join(tokens[1:]),
                        '%Y/%m/%d %H:%M:%S')

        else:
                raise Exception('Parse error in timestamp')


def timestamp_is_ge(t1, t2):
        if t1 == 'never':
                return True

        elif t2 == 'never':
                return False

        else:
                return t1 >= t2


def timestamp_is_lt(t1, t2):
        if t1 == 'never':
                return False

        elif t2 == 'never':
                return t1 != 'never'

        else:
                return t1 < t2


def timestamp_is_between(t, tstart, tend):
        return timestamp_is_ge(t, tstart) and timestamp_is_lt(t, tend)


def parse_hardware(raw_str):
        tokens = raw_str.split()

        if len(tokens) == 2:
                return tokens[1]

        else:
                raise Exception('Parse error in hardware')


def strip_endquotes(raw_str):
        return raw_str.strip('"')


def identity(raw_str):
        return raw_str


def parse_binding_state(raw_str):
        tokens = raw_str.split()

        if len(tokens) == 2:
                return tokens[1]

        else:
                raise Exception('Parse error in binding state')


def parse_next_binding_state(raw_str):
        tokens = raw_str.split()

        if len(tokens) == 3:
                return tokens[2]

        else:
                raise Exception('Parse error in next binding state')


def parse_rewind_binding_state(raw_str):
        tokens = raw_str.split()

        if len(tokens) == 3:
                return tokens[2]

        else:
                raise Exception('Parse error in next binding state')


def parse_leases_file(leases_file):
        valid_keys = {
                'starts':               parse_timestamp,
                'ends':                 parse_timestamp,
                'tstp':                 parse_timestamp,
                'tsfp':                 parse_timestamp,
                'atsfp':                parse_timestamp,
                'cltt':                 parse_timestamp,
                'hardware':             parse_hardware,
                'binding':              parse_binding_state,
                'next':                 parse_next_binding_state,
                'rewind':               parse_rewind_binding_state,
                'uid':                  strip_endquotes,
                'client-hostname':      strip_endquotes,
                'option':               identity,
                'set':                  identity,
                'on':                   identity,
                'abandoned':            None,
                'bootp':                None,
                'reserved':             None,
                }

        leases_db = {}

        lease_rec = {}
        in_lease = False

        for line in leases_file:
                if line.lstrip().startswith('#'):
                        continue

                tokens = line.split()

                if len(tokens) == 0:
                        continue

                key = tokens[0].lower()

                if key == 'lease':
                        if not in_lease:
                                ip_address = tokens[1]

                                lease_rec = {'ip-address' : ip_address}
                                in_lease = True

                        else:
                                raise Exception('Parse error in leases file')

                elif key == '}':
                        if in_lease:
                                for k in valid_keys:
                                        if callable(valid_keys[k]):
                                                lease_rec[k] = lease_rec.get(k, '')
                                        else:
                                                lease_rec[k] = False

                                ip_address = lease_rec['ip-address']

                                if ip_address in leases_db:
                                        leases_db[ip_address].insert(0, lease_rec)

                                else:
                                        leases_db[ip_address] = [lease_rec]

                                lease_rec = {}
                                in_lease = False

                        else:
                                raise Exception('Parse error in leases file')

                elif key in valid_keys:
                        if in_lease:
                                value = line[(line.index(key) + len(key)):]
                                value = value.strip().rstrip(';').rstrip()
                                
                                if callable(valid_keys[key]):
                                        lease_rec[key] = valid_keys[key](value)
                                else:
                                        lease_rec[key] = True

                        else:
                                raise Exception('Parse error in leases file')

                else:
                        if in_lease:
                                raise Exception('Parse error in leases file')

        if in_lease:
                raise Exception('Parse error in leases file')

        return leases_db


def round_timedelta(tdelta):
        return datetime.timedelta(tdelta.days,
                tdelta.seconds + (0 if tdelta.microseconds < 500000 else 1))


def timestamp_now():
        n = datetime.datetime.utcnow()
        return datetime.datetime(n.year, n.month, n.day, n.hour, n.minute,
                n.second + (0 if n.microsecond < 500000 else 1))


def lease_is_active(lease_rec, as_of_ts):
        return timestamp_is_between(as_of_ts, lease_rec['starts'],
                lease_rec['ends'])


def ipv4_to_int(ipv4_addr):
        parts = ipv4_addr.split('.')
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + \
                (int(parts[2]) << 8) + int(parts[3])


def select_active_leases(leases_db, as_of_ts):
        retarray = []
        sortedarray = []

        for ip_address in leases_db:
                lease_rec = leases_db[ip_address][0]

                if lease_is_active(lease_rec, as_of_ts):
                        ip_as_int = ipv4_to_int(ip_address)
                        insertpos = bisect.bisect(sortedarray, ip_as_int)
                        sortedarray.insert(insertpos, ip_as_int)
                        retarray.insert(insertpos, lease_rec)

        return retarray


##############################################################################

class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return time.mktime(obj.timetuple())
        return json.JSONEncoder.default(self, obj)

def ping(ip):
    try:
        output = subprocess.check_output(["ping", "-c1", "-w1 ", ip])
    except subprocess.CalledProcessError:
        return False
    return True

def test_pingable(dataset):
    rv = []
    for item in dataset:
        ip = item['ip-address']
        canPing = ping(ip)
        item['ping'] = canPing
        if canPing:
        	item['alive'] = True
        rv.append(item)
    return rv
    
def parse_arp():
    try:
        output = subprocess.check_output(['arp', '-an'], universal_newlines=True)
    except subprocess.CalledProcessError:
        return []
    rv = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[2] != 'at': continue
        ip = fields[1]
        arp = fields[3]
        if ip[0] != '(' or ip[-1] != ')': continue
        ip = ip[1:-1]
        rv[ip] = arp
    return rv
    
def test_arp(dataset):
    arphosts = parse_arp()
    rv = []
    for item in dataset:
        ip = item['ip-address']
        mac = item['hardware']
        canArp = (ip in arphosts and arphosts[ip] == mac)
        item['arp'] = canArp
        if canArp:
        	item['alive'] = True
        rv.append(item)
    return rv
    
def filter_keys(dataset, keys):
    rv = []
    for item in dataset:
        newItem = {}
        for k in keys:
            if k in item:
                newItem[k] = item[k]
        rv.append(newItem)
    return rv
    
