#!/bin/sh
PATH=$PATH:/usr/local/bin:$HOME/bin
set -vx
case x$igor_remoteHost in
x)
	tmutil=tmutil
	;;
xlocalhost)
	tmutil=tmutil
	;;
*)
	tmutil="ssh $igor_remoteHost tmutil"
	;;
esac
case x$igor_name in
x)
	igor_name=backup
	;;
esac
backupFilename=`$tmutil latestbackup 2>&1`
if [ $? -ne 0 ]; then
	cat << endcat | igorVar --post application/json --checkdata /internal/updateStatus
{ "representing" : "services/$igor_name",
  "alive" : false,
  "resultData" : "$igor_name status cannot be determined: $backupFilename"
}
endcat
	
else
	backupTime=`echo "$backupFilename" | sed -e 's@.*/\([0-9][[0-9][0-9][0-9]\)-\([0-9][0-9]\)-\([0-9][0-9]\)-\([0-9][0-9]\)\([0-9][0-9]\)\([0-9][0-9]\)@\1-\2-\3 \4:\5:\6@'`
	cat << endcat | igorVar --post application/json --checkdata /internal/updateStatus/services/$igor_name
{ "alive" : true,
  "lastSuccess" : "$backupTime",
  "resultData" : ""
}
endcat
fi
