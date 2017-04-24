#!/bin/bash
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
dir=`dirname $0`
command="python $dir/rfidread.py --server"
echo "START IS CALLED"
case "x$igor_host" in
x)
	;;
'x{}')
	# Workaround....
	;;
x*)
	command="ssh $igor_host $command"
	;;
esac
case "x$igor_serial" in
x)
	;;
x*)
	command="$command --line $igor_serial"
	;;
esac
case "x$igor_baud" in
x)
	;;
x*)
	command="$command --baud $igor_baud"
	;;
esac
case "x$igor_url" in
x)
	;;
x*)
	command="$command --url '$igor_url'"
	;;
esac
echo 'iirfid start' $command
$command  >iirfid.$$.log 2>&1 &
