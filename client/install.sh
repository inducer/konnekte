#! /bin/sh
DESTLIBDIR=/usr/local/lib/konnekte
DESTSHAREDIR=/usr/local/share/konnekte
rm -Rf $DESTLIBDIR
mkdir -p $DESTLIBDIR
rm -Rf $DESTSHAREDIR
mkdir -p $DESTSHAREDIR

cp *.py $DESTLIBDIR
cp *.desktop $DESTSHAREDIR
cp images/*.png $DESTSHAREDIR

(cd /usr/local/bin; rm -f konnekte; ln -s $DESTLIBDIR/konnekte-client.py konnekte)
(cd /usr/share/icons/hicolor/48x48/apps; rm -f konnekte.png; ln -s $DESTSHAREDIR/main.png konnekte.png)
(cd /usr/share/applications; rm -f konnekte.desktop; ln -s $DESTSHAREDIR/konnekte.desktop .)
