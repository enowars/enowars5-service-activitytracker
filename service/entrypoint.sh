#!/bin/sh
set -e
set -x

mkdir -p /data/imgs
mkdir -p /data/imgs/profiles

# wait for database connection
until nc -vz -w 100 postgres 5432
do
  sleep 1
done

# wait until db system is started up
until diesel setup
do
  sleep 1
done
diesel migration run

cargo run --release