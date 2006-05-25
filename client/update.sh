#! /bin/bash
for i in ui/*.ui; do
  BN=`basename $i`
  pyuic $i > ui_${BN%.ui}.py
done
pylupdate konnekte.pro
lrelease konnekte.pro
./makedata images/*.png *.qm > binary_data.py
