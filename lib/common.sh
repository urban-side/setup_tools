#!/bin/bash
# 各 install スクリプトから source して使う共通ヘルパ。
#
# REPO_ROOT はこのファイル自身の位置から解決するため、呼び出し元の
# カレントディレクトリに依存しない。リポジトリ内のファイルを指すときは
# 必ず "${REPO_ROOT}/..." を使うこと。

# shellcheck disable=SC2155
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export REPO_ROOT

log()  { printf '🚀 %s\n' "$*"; }
ok()   { printf '✅ %s\n' "$*"; }
skip() { printf '⏭️  %s\n' "$*"; }
warn() { printf '⚠️  %s\n' "$*"; }

# 変更を反映するために再起動が必要なプロセスを落とす。
# 対象が起動していない場合 killall は 1 を返すが、それは失敗ではないので握りつぶす。
refresh_process() {
  local name="$1"
  killall "$name" 2>/dev/null || true
}
