from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
from . import _kaku

def main():
	if len(sys.argv) < 3 or sys.argv[1] not in ("on", "off"):
		print("Usage: %s on|off switchnum [...]" % sys.argv[0], file=sys.stderr)
		sys.exit(1)
	k = _kaku.TPC300()
	if sys.argv[1] == 'on':
		cmd = 3
		a3 = 16
	else:
		cmd = 1
		a3 = 0
	for num in sys.argv[2:]:
		k.send(cmd, int(num), a3)

if __name__ == '__main__':
	main()	
