#!/bin/sh
set -e
set -x

mkdir -p /data/imgs

until nc -vz -w 100 postgres 5432
do
  sleep 1
done

diesel setup
diesel migration run

cargo run --release