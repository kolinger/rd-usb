@echo off

rem first argument %1 is path to JSON file containing measurements

rem read and process temporary file
rem in this example JSON will be appended to on-receive.output file, for testing purpose
rem here we can parse/format this JSON and send data somewhere else
type "%1" >> on-receive.output
echo "" >> on-receive.output

rem delete temporary file
del "%1"
