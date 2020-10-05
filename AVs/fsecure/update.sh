#!/bin/bash

/etc/init.d/fsaua start
/etc/init.d/fsupdate start
# added dbupdate_lite script for definitions update
/opt/f-secure/fssp/bin/dbupdate_lite
/opt/f-secure/fsdbupdate9.run; exit 0
