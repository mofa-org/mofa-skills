#!/bin/bash
# DEPRECATED: Deploy all mofa skills to a Mac Mini profile/sub-account.
# Usage: ./scripts/deploy-mini.sh [mini1|mini3] [profile]
#
# This script is deprecated. Use the fleet-install script in the octos repo
# instead — it routes through `octos skills install` so every install is
# sha256-verified and resolves the correct per-profile target directory:
#
#     /Users/yuechen/home/octos/scripts/fleet-install-skills.sh --host <hosts>
#
# To run this legacy script anyway (raw scp, no sha256 verification, single
# hard-coded profile path), set OCTOS_DEPRECATED_SCP=1.
set -euo pipefail

echo >&2 "ERROR: deploy-mini.sh is deprecated. Use:"
echo >&2 "  /Users/yuechen/home/octos/scripts/fleet-install-skills.sh --host <hosts>"
echo >&2 "Falling back to legacy behavior. Suppress this warning by setting OCTOS_DEPRECATED_SCP=1."
[ -n "${OCTOS_DEPRECATED_SCP:-}" ] || exit 1


MINI="${1:-mini1}"
PROFILE="${2:-dspfac}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/scripts}"

case "$MINI" in
  mini1)
    IP="69.194.3.128"
    PW="zjsgf128"
    ;;
  mini3)
    IP="69.194.3.203"
    PW="b_KPfpN7Ge2ggxF-"
    ;;
  *)
    echo "Usage: $0 [mini1|mini3] [profile]" >&2
    exit 1
    ;;
esac

SSH="sshpass -p '$PW' ssh -o StrictHostKeyChecking=no cloud@$IP"
SCP="sshpass -p '$PW' scp -o StrictHostKeyChecking=no"
REMOTE_SKILLS="/Users/cloud/.octos/profiles/$PROFILE/data/skills"

echo "=== Deploying mofa-skills to $MINI ($IP) profile=$PROFILE ==="
echo ""

# Skills to deploy — each dir under mofa-skills/ that has a SKILL.md
SKILLS=()
for d in "$REPO_DIR"/mofa-*/; do
  [ -f "$d/SKILL.md" ] || continue
  name=$(basename "$d")
  SKILLS+=("$name")
done

echo "Skills to deploy: ${SKILLS[*]}"
echo ""

# Deploy each skill
for skill in "${SKILLS[@]}"; do
  src="$REPO_DIR/$skill"
  echo "--- $skill ---"

  # Create remote dir
  eval $SSH "'mkdir -p $REMOTE_SKILLS/$skill'"

  # Sync files: SKILL.md, manifest.json, main, *.dot, styles/, scripts/, templates/
  files_to_copy=()

  # Always copy SKILL.md
  [ -f "$src/SKILL.md" ] && files_to_copy+=("$src/SKILL.md")

  # manifest.json
  [ -f "$src/manifest.json" ] && files_to_copy+=("$src/manifest.json")

  # main executable
  if [ -f "$src/main" ]; then
    files_to_copy+=("$src/main")
  fi

  # .dot files
  for f in "$src"/*.dot; do
    [ -f "$f" ] && files_to_copy+=("$f")
  done

  # Copy flat files
  if [ ${#files_to_copy[@]} -gt 0 ]; then
    eval $SCP "${files_to_copy[*]}" "cloud@$IP:$REMOTE_SKILLS/$skill/"
  fi

  # Copy directories (styles, scripts, templates)
  for subdir in styles scripts templates; do
    if [ -d "$src/$subdir" ]; then
      eval $SCP "-r $src/$subdir" "cloud@$IP:$REMOTE_SKILLS/$skill/"
    fi
  done

  # Make main executable if it exists
  if [ -f "$src/main" ]; then
    eval $SSH "'chmod +x $REMOTE_SKILLS/$skill/main'"
    echo "  main: deployed + chmod +x"
  fi

  # Make shell scripts executable
  if [ -d "$src/scripts" ]; then
    eval $SSH "'chmod +x $REMOTE_SKILLS/$skill/scripts/*.sh 2>/dev/null || true'"
  fi

  echo "  done"
done

echo ""

# Verify deployment
echo "=== Verifying ==="
eval $SSH "'for d in $REMOTE_SKILLS/mofa-*/; do
  name=\$(basename \"\$d\")
  has_skill=\$(test -f \"\$d/SKILL.md\" && echo \"✓\" || echo \"✗\")
  has_manifest=\$(test -f \"\$d/manifest.json\" && echo \"✓\" || echo \"✗\")
  has_main=\$(test -f \"\$d/main\" -o -f \"\$d/mofa\" && echo \"✓\" || echo \"✗\")
  echo \"  \$name  SKILL.md=\$has_skill manifest=\$has_manifest exec=\$has_main\"
done'"

echo ""
echo "=== Deploy complete ==="
echo "Skills may require a gateway restart to pick up changes."
echo "Run: launchctl kickstart -k gui/\$(id -u)/io.ominix.octos-serve"
