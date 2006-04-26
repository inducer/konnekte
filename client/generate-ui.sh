#! /bin/bash
for i in ui/*.ui; do
  BN=`basename $i`
  pyuic $i > ui-${BN%.ui}.py
done
