"""Match list of supported mimetypes to an Accept: header"""
from __future__ import print_function
from __future__ import unicode_literals
import sys

class MimetypeError(ValueError):
    pass
    
def _match1(acceptable, mimetype):
    asplit = acceptable.split('/')
    msplit = mimetype.split('/')
    if len(asplit) != 2:
        raise ValueError("Accept header mimetype not of form type/subtype")
    if len(msplit) != 2:
        raise ValueError("Mimetype not of form type/subtype")
    if asplit[0] != msplit[0] and asplit[0] != '*':
        return False
    if asplit[1] != msplit[1] and asplit[1] != '*':
        return False
    return True
    
def match(acceptable, mimetypelist):
    alist = []
    for a in acceptable.split(','):
        if ';' in a:
            a = a.split(';')[0]
        a = a.strip()
        alist.append(a)
    for mimetype in mimetypelist:
        for a in alist:
            if _match1(a, mimetype):
                return mimetype
    return None

def main(): # pragma: no cover
    if len(sys.argv) < 3:
        print("Usage: %s acceptheader mimetype [...]" % sys.argv[0], file=sys.stderr)
        sys.exit(2)
    acceptable = sys.argv[1]
    mimetypelist = sys.argv[2:]
    best = match(acceptable, mimetypelist)
    if best:
        print(best)
        sys.exit(0)
    sys.exit(1)
    
if __name__ == '__main__':
    main()
