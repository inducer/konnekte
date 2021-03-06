#! /bin/sh
DESTMACHINE=sprite

ssh root@$DESTMACHINE "mkdir -p konnekte/bin"
ssh root@$DESTMACHINE "mkdir -p konnekte/etc"
ssh root@$DESTMACHINE "mkdir -p konnekte/var"
ssh root@$DESTMACHINE "mkdir -p konnekte/ppp"
scp -r router/bin/konnekte root@$DESTMACHINE:konnekte/bin
scp -r router/etc/*[a-zA-Z] root@$DESTMACHINE:konnekte/etc
scp -r router/ppp/*[a-zA-Z] root@$DESTMACHINE:konnekte/ppp
