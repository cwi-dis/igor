import sys
import os
import bluetooth._bluetooth as bluez
import igorServlet
from .bleServer import BleScanServer
       
def main():
    parser = igorServlet.IgorServlet.argumentParser()
    parser.add_argument('--installDaemon', action="store_true", help="List commands needed to install bleServer as a daemon")
    args = parser.parse_args()
    if args.installDaemon:
        baseDir = os.path.dirname(__file__)
        initPath = os.path.join(baseDir, "initscript-bleServer")
        if not os.path.exists(initPath):
            print(f"Init.d script missing: {initPath}")
            sys.exit(1)
        print("# Run the following commands:")
        print("(")
        print(f"\tsudo cp {initPath} /etc/init.d/bleServer")
        print("\tsudo update-rc.d bleServer defaults")
        print("\tsudo service bleServer start")
        print(")")
        sys.exit(0)
    try:
        bleScanner = BleScanServer(**vars(args))
    except bluez.error as e:
        if e.args == (1, 'Operation not permitted'):
            print('Must run as root, ble scanning not allowed for normal users (sigh).')
            sys.exit(1)
        raise
    bleScanner.run()
    
if __name__ == '__main__':
    main()
    print('stopped.')
