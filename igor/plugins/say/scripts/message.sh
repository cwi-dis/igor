#!/bin/sh
case x$igor_remoteHost in
x)
	say=say
	;;
*)
	say="ssh $igor_remoteHost say"
	;;
esac
case x$igor_voice in
x)
	sayArg=
	;;
x*)
	sayArg="-v $igor_voice"
	;;
esac
$say $sayArg $@
