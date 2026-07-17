#!/bin/bash
set -e
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; N='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_USER="${SUDO_USER:-$USER}"; USER_HOME=$(eval echo "~$REAL_USER")
INSTALL_DIR="$USER_HOME/rabbit_racer"; VENV="$USER_HOME/rabbit_racer_env"
APPS="$USER_HOME/.local/share/applications"; BIN="$INSTALL_DIR/bin/rabbit-racer"
STEPS=7; step(){ echo -e "\n${G}[$1/$STEPS]${N} ${C}$2${N}"; }
ok(){ echo -e "  ${G}✔${N} $1"; }; fail(){ echo -e "${R}✘ $1${N}"; exit 1; }

printf "${Y}  RABBIT RACER v3 — INSTALLER${N}\n\n"
[ "$EUID" -ne 0 ] && fail "Run: sudo ./rbitgm.sh"; ok "root ok (user: $REAL_USER)"

step 1 "System packages (SDL2, audio, dev libs — not python)"
apt-get update -qq 2>/dev/null && apt-get install -y -qq \
  python3-pip python3-venv python3-dev libsdl2-dev libsdl2-image-dev \
  libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libjpeg-dev \
  libfreetype6-dev binutils upx-ucl patchelf 2>/dev/null
ok "System deps installed"

step 2 "Virtualenv + pip"
sudo -u "$REAL_USER" python3 -m venv "$VENV"
sudo -u "$REAL_USER" "$VENV/bin/pip" install -q --upgrade pip setuptools wheel
ok "venv at $VENV"

step 3 "pygame + pyinstaller"
sudo -u "$REAL_USER" "$VENV/bin/pip" install -q pygame pyinstaller
ok "pygame + pyinstaller ready"

step 4 "Deploying game + uninstaller"
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/game.py"      "$INSTALL_DIR/game.py"
cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/uninstall.sh"
chmod +x "$INSTALL_DIR/uninstall.sh"
chown -R "$REAL_USER":"$REAL_USER" "$INSTALL_DIR"
ok "game.py + uninstall.sh deployed"

step 5 "PyInstaller build (1-3 min on Pi)"
echo -e "  ${Y}Compiling standalone binary...${N}"
sudo -u "$REAL_USER" "$VENV/bin/pyinstaller" --onefile \
  --name "rabbit-racer" --distpath "$INSTALL_DIR/bin" \
  --workpath "$INSTALL_DIR/build" --specpath "$INSTALL_DIR" \
  --hidden-import pygame --hidden-import pygame.mixer \
  --hidden-import pygame.font --hidden-import pygame.draw \
  --hidden-import pygame.transform --hidden-import pygame.event \
  --hidden-import pygame.mouse --hidden-import pygame.time \
  --collect-all pygame --noconfirm --clean \
  "$INSTALL_DIR/game.py" 2>&1 | grep -E "^(INFO|WARN|ERROR|Building)" || true
[ -f "$BIN" ] || fail "PyInstaller failed — binary missing at $BIN"
chmod +x "$BIN"; chown "$REAL_USER":"$REAL_USER" "$BIN"
rm -rf "$INSTALL_DIR/build" "$INSTALL_DIR/rabbit-racer.spec"
ok "Binary: $BIN ($(du -sh "$BIN" | cut -f1))"

step 6 "System command"
ln -sf "$BIN" /usr/local/bin/rabbit-racer
ok "/usr/local/bin/rabbit-racer → $BIN"

step 7 "Games menu shortcut"
sudo -u "$REAL_USER" mkdir -p "$APPS"
cat > "$APPS/rabbit-racer.desktop" << DESK
[Desktop Entry]
Name=Rabbit Racer
GenericName=Arcade Game
Comment=Pixel arcade — dodge cars! LMB=gas RMB=brake Mouse=steer
Exec=$BIN
Icon=applications-games
Type=Application
Categories=Game;ArcadeGame;
Terminal=false
StartupNotify=true
DESK
chmod +x "$APPS/rabbit-racer.desktop"
chown "$REAL_USER":"$REAL_USER" "$APPS/rabbit-racer.desktop"
update-desktop-database "$APPS" 2>/dev/null || true
ok "Games menu shortcut created"

echo -e "\n${G}  ✅ Rabbit Racer v3 installed!${N}"
echo -e "  Launch:    ${Y}rabbit-racer${N}  or  Games menu"
echo -e "  Controls:  Mouse=steer  LMB=accelerate  RMB=brake"
echo -e "  Cheat:     Middle-click x5 then scroll up"
echo -e "  Uninstall: ${Y}sudo $INSTALL_DIR/uninstall.sh${N}\n"
