#!/usr/bin/env bash
# Creates the git worktree of one phase B lane (ADR 0010, section 6).
#
#   scripts/worktree-setup.sh <l1..l8>
#
# The worktree lives in .worktrees/<lane> on the branch feat/b-<lane>, cut from main. Inputs that
# the lane only reads are symlinked to the main checkout; outputs that the lane regenerates are
# cloned (APFS copy-on-write), so lanes never overwrite each other's generated assets.
set -euo pipefail

lane="${1:-}"
case "$lane" in
  l[1-8]) ;;
  *)
    echo "usage: scripts/worktree-setup.sh <l1..l8>" >&2
    exit 2
    ;;
esac
number="${lane#l}"

die() {
  echo "worktree-setup: $1" >&2
  exit 1
}

root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "run it inside the penyal-ifac-3d repository."
cd "$root"

git_dir="$(git rev-parse --path-format=absolute --git-dir)"
common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
[ "$git_dir" = "$common_dir" ] || die "run it from the main checkout ($(dirname "$common_dir")), not from a worktree."
[ -z "$(git status --porcelain)" ] || die "the working tree is not clean. Commit or stash first: the lane starts from main."
git show-ref --verify --quiet refs/heads/main || die "there is no main branch to cut the lane from."

worktree="$root/.worktrees/$lane"
branch="feat/b-$lane"
[ ! -e "$worktree" ] || die "$worktree already exists. Remove it first: git worktree remove --force .worktrees/$lane"
! git show-ref --verify --quiet "refs/heads/$branch" || die "the branch $branch already exists. Delete it or pick the lane's existing worktree."

git worktree add "$worktree" -b "$branch" main

# Inputs: read-only, absolute links into the main checkout.
link() {
  local from="$1"
  [ -e "$root/$from" ] || return 0
  mkdir -p "$(dirname "$worktree/$from")"
  ln -s "$root/$from" "$worktree/$from"
}
link data/raw
link data/manual
link tools/bin
for ktx in "$root"/tools/ktx-*; do
  [ -e "$ktx" ] && link "tools/$(basename "$ktx")"
done

# Outputs: each lane regenerates its own, so they are cloned, not linked.
clone() {
  local from="$1"
  [ -e "$root/$from" ] || return 0
  mkdir -p "$(dirname "$worktree/$from")"
  if ! cp -cR "$root/$from" "$worktree/$from" 2>/dev/null; then
    echo "worktree-setup: this volume cannot clone files; making a full copy of $from." >&2
    rm -rf "${worktree:?}/$from"
    cp -R "$root/$from" "$worktree/$from"
  fi
}
clone build
clone app/public/assets/generated

(cd "$worktree" && pnpm install --frozen-lockfile)
(cd "$worktree" && uv sync --project pipeline --locked)

cat <<MESSAGE

Worktree ready: .worktrees/$lane (branch $branch)
  E2E port:     $((5180 + number))   (E2E_OUTPUT_DIR defaults to test-results/$lane)
  Dev server:   pnpm --filter @penyal/app dev --port $((5190 + number))
  Remove it:    git worktree remove --force .worktrees/$lane && git branch -D $branch
MESSAGE
