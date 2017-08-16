#!/bin/sh
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi
case `which say` in
*say)
	;;
*)
	say() {
		if which espeak; then
			espeak "$*"
		elif which flite; then
			flite "$*"
		elif which festival; then
			echo "$*" | festival --tts
		else
			echo "For speech output Install speak, flite or festival if you do not have say"
			exit 1
		fi
	}
esac
case x$igor_remoteHost in
x)
	say=say
	;;
*)
	# Remote assumes OSX, for now....
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
$say $sayArg "$@"
