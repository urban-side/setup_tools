#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/macos/install.sh"
bash "${SCRIPT_DIR}/home/install.sh"
bash "${SCRIPT_DIR}/claude/install.sh"
bash "${SCRIPT_DIR}/apps/install.sh"
