#!/bin/bash

i=$(xdotool getactivewindow)
echo "$i $(xdotool getwindowname $i)"
echo

xprop -root | \
    sed -n '/_NET_CLIENT_LIST_STACKING(WINDOW)/s/^[^#]*# \(.*\)$/\1/p' | \
    sed 's/, /\n/g' | \
    while read i; do
        OUT="$i"
        WPID="$(xdotool getwindowpid $i 2>/dev/null)"
        if [ $? = 0 ]; then
            OUT="$OUT pid=$WPID"
        fi
        echo "$OUT $(xdotool getwindowname $i)"
    done
