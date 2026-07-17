#!/bin/bash
# ============================================================
#  Rabbit Racer — Uninstaller
#  Usage: sudo ./uninstall.sh
#  Removes EVERYTHING including this script itself.
# ============================================================
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; N='\033[0m'

if [ "$EUID" -ne 0 ]; then
  echo -e "${R}Run with sudo: sudo ./uninstall.sh${N}"; exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$REAL_USER")
SELF="$(realpath "$0")"

echo -e "${Y}Rabbit Racer Uninstaller${N}"
echo -e "${R}This will remove all Rabbit Racer files.${N}"
read -p "Continue? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

ok()   { echo -e "  ${G}✔${N} $1"; }
skip() { echo -e "  ${Y}–${N} $1 (not found)"; }

# Game binary and build
if   [ -d "$USER_HOME/rabbit_racer" ];    then rm -rf "$USER_HOME/rabbit_racer";    ok "Removed ~/rabbit_racer/"; else skip "~/rabbit_racer"; fi
# Virtual environment
if   [ -d "$USER_HOME/rabbit_racer_env" ]; then rm -rf "$USER_HOME/rabbit_racer_env"; ok "Removed ~/rabbit_racer_env/"; else skip "~/rabbit_racer_env"; fi
# Desktop shortcut
DESK="$USER_HOME/.local/share/applications/rabbit-racer.desktop"
if   [ -f "$DESK" ]; then rm -f "$DESK"; update-desktop-database "$(dirname $DESK)" 2>/dev/null; ok "Removed .desktop shortcut"; else skip ".desktop"; fi
# System symlink
if   [ -L "/usr/local/bin/rabbit-racer" ]; then rm -f /usr/local/bin/rabbit-racer; ok "Removed /usr/local/bin/rabbit-racer"; else skip "/usr/local/bin symlink"; fi
# High score save
SAVE="$USER_HOME/.rbitgm_save.json"
if   [ -f "$SAVE" ]; then rm -f "$SAVE"; ok "Removed high score save"; else skip "High score save"; fi
# The installer zip/folder (if still in Downloads)
for f in "$USER_HOME/Downloads/rbitgm.zip" "$USER_HOME/Downloads/rbitgm"; do
  [ -e "$f" ] && rm -rf "$f" && ok "Removed $f" || true
done

echo ""
echo -e "${G}✅ Rabbit Racer fully uninstalled.${N}"

# Remove this script last (schedule via subshell so script finishes cleanly)
SELF_DIR="$(dirname "$SELF")"
(sleep 1 && rm -f "$SELF" && rmdir --ignore-fail-on-non-empty "$SELF_DIR" 2>/dev/null) &
echo -e "  ${Y}Uninstaller removed itself.${N}"
