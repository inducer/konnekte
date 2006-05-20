#! /bin/sh
DESTMACHINE=sprite

ssh root@$DESTMACHINE "rm -R konnekte"
ssh root@$DESTMACHINE "mkdir -p konnekte/bin"
ssh root@$DESTMACHINE "mkdir -p konnekte/etc"
ssh root@$DESTMACHINE "mkdir -p konnekte/var"
scp -r ../router/var/* root@$DESTMACHINE:konnekte/var
scp -r ../router/etc/* root@$DESTMACHINE:konnekte/etc
scp -r ../router/bin/* root@$DESTMACHINE:konnekte/bin
