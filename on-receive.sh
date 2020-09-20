#!/bin/bash

# first argument $1 is path to JSON file containing measurements

# read and process temporary file
# in this example JSON will be appended to on-receive.output file, for testing purpose
# here we can parse/format this JSON and send data somewhere else
cat "$1" >> on-receive.output
echo "" >> on-receive.output

# delete temporary file
rm "$1"
