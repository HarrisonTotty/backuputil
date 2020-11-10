#!/usr/bin/env bash
# Simple script for testing purposes.

set -e

export BACKUPUTIL_BORG_PATH='/usr/bin/borg'
export BACKUPUTIL_CONFIG_FILE='example/backuputil.yaml'
export BACKUPUTIL_LOG_FILE='/tmp/backuputil.log'
export BACKUPUTIL_LOG_LVL='debug'
export BACKUPUTIL_LOG_MODE='overwrite'

./backuputil.py $@
