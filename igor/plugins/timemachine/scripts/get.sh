#!/bin/sh
case x$igor_remoteHost in
x)
	tmutil=tmutil
	;;
*)
	tmutil = "ssh $igor_remoteHost tmutil"
	;;
esac
case x$igor_name in
x)
	igor_name=backup
	;;
esac
backupFilename=`$tmutil latestbackup`
if [ $? -ne 0 ]; then
	igorVar --put text/plain --data "" services/$igor_name/alive
	igorVar --put text/plain --data "$backupFilename" services/$igor_name/errorMessage
else
	igorVar --put text/plain --data "true" services/$igor_name/alive
	backupTime=`echo "$backupFilename" | sed -e 's@.*/\([0-9][[0-9][0-9][0-9]\)-\([0-9][0-9]\)-\([0-9][0-9]\)-\([0-9][0-9]\)\([0-9][0-9]\)\([0-9][0-9]\)@\1-\2-\3 \4:\5:\6@'`
	igorVar --put text/plain --data "$backupTime" services/$igor_name/lastActivity
fi
