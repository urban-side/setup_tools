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

# 内容が変わっているときだけコピーする。再実行時に何が実際に変わったかが
# ログに残り、mtime も無用に更新されない。
copy_if_changed() {
  local src="$1" dst="$2" label="${3:-$(basename "$1")}"
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    skip "${label} は最新です"
  else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    ok "${label} を更新しました"
  fi
}

# ディレクトリを丸ごと同期する。リポジトリ側で削除したファイルを配置先からも
# 消すため、cp -R ではなく rsync --delete を使う。
sync_dir() {
  local src="$1" dst="$2" label="${3:-$(basename "$1")}"
  mkdir -p "$dst"
  local out
  out="$(rsync -rlpt --delete --itemize-changes "${src%/}/" "${dst%/}/")"
  if [ -z "$out" ]; then
    skip "${label} は最新です"
  else
    printf '%s\n' "$out" | sed 's/^/    /'
    ok "${label} を同期しました"
  fi
}

# 行が無ければ追記する。既にあれば何もしない。
append_line_once() {
  local file="$1" line="$2" label="${3:-$1}"
  [ -f "$file" ] || touch "$file"
  if grep -Fqx "$line" "$file"; then
    skip "${label} は既に設定済みです"
  else
    printf '%s\n' "$line" >> "$file"
    ok "${label} に設定を追加しました"
  fi
}
