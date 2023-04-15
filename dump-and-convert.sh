#!/bin/bash
echo "What channel should be exported?"
echo "Please enter the internal channel ID of slack (eg. GSE6ZQDHT)"
read -r channel
./slackdump -download -base data/messages "$channel"
slackdump2html data/messages "$channel"
read -p "Press Enter to finish" </dev/tty
