#!/bin/sh
set -e
set -x

diesel setup
diesel migration run
cargo run