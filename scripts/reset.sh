#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

mkdir -p data/generated_letters data/logs data/session

rm -rf data/generated_letters/*
rm -rf data/logs/*
rm -rf data/session/*

cat > data/state.json <<'EOF'
{
  "jobs": {}
}
EOF

touch data/generated_letters/.gitkeep
touch data/logs/.gitkeep
touch data/session/.gitkeep

printf 'Reset complete.\n'
