import logging

logging.basicConfig()

def install(logSpec):
    if logSpec == None:
        return
    for ll in logSpec.split(','):
        if ':' in ll:
            loggerToModify = logging.getLogger(ll.split(':')[0])
            newLevel = getattr(logging, ll.split(':')[1])
        else:
            loggerToModify = logging.getLogger()
            newLevel = getattr(logging, ll)
        loggerToModify.setLevel(newLevel)
