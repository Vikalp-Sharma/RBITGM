<div align="center">

```
██████╗ ██████╗ ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██╔══██╗██║╚══██╔══╝██╔════╝ ████╗ ████║
██████╔╝██████╔╝██║   ██║   ██║  ███╗██╔████╔██║
██╔══██╗██╔══██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║  ██║██████╔╝██║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝  ╚═╝╚═════╝ ╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
```

### 🐇 Rabbit Racer — installer codename `rbitgm`

[![Python](https://img.shields.io/badge/python-3.9%2B-2b5b84?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Engine](https://img.shields.io/badge/engine-pygame%202-66c07a?style=for-the-badge&logo=python&logoColor=white)](https://www.pygame.org/)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20%2F%20Linux-c0392b?style=for-the-badge&logo=raspberrypi&logoColor=white)](#requirements)
[![Build](https://img.shields.io/badge/build-PyInstaller%20onefile-f4b942?style=for-the-badge&logo=pyinstaller&logoColor=black)](#installation)
[![Status](https://img.shields.io/badge/status-passing-3ddc84?style=for-the-badge)](#)
[![Version](https://img.shields.io/badge/version-v3-7c5cff?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-e63946?style=for-the-badge)](LICENSE)
[![No Copying](https://img.shields.io/badge/copying-not%20permitted-e63946?style=for-the-badge)](LICENSE)
[![Made By](https://img.shields.io/badge/made%20by-Vikalp%20Sharma-00c2ff?style=for-the-badge)](#)

**A pixel-art arcade dodging game — steer with your mouse, dodge traffic, chase the high score.**

</div>

---

## About

Rabbit Racer is a self-contained top-down arcade racer built with `pygame`. You play a rabbit behind the wheel (with a rottweiler riding shotgun), weaving through a procedurally spawned 3-lane highway of traffic. Grab coins, collect power-ups, obey the odd red light, and try not to total the car.

The whole thing ships as a **one-command installer** (`rbitgm.sh`) that builds a native standalone binary on your machine (great for Raspberry Pi), drops a Games-menu shortcut, and registers a system-wide `rabbit-racer` command — plus a clean one-command uninstaller.

## Features

- 🚗 **Dynamic, resizable 3–10 lane highway** — the road adapts lane count to your window size
- 🪙 **Coins, power-ups & combos** — shields, time-slow, and coin-doubler pickups
- 🚦 **Traffic lights & zebra crossings** with pedestrians who actually cross
- 🌙 **Day/night cycle** that kicks in as you level up
- 💥 **Particles, skid marks, screen shake** — small juice, big feel
- 🏆 **Persistent high score**, saved locally
- 🎮 **Mouse-only controls** — steer, accelerate, brake, no keyboard required
- 🕹️ A not-so-secret **cheat code**
- 📦 **Standalone binary build** via PyInstaller — no Python needed to *run* it after install

## Controls

| Input | Action |
|---|---|
| Mouse move | Steer |
| Left click (hold) | Accelerate |
| Right click (hold) | Brake |
| `P` | Pause |
| Middle-click ×5, then scroll up | Cheat mode |
| `Esc` | Quit (auto-saves high score) |

## Installation

Requires a Debian/Ubuntu-based Linux system (built and tested for Raspberry Pi OS). The installer handles everything else — system packages, the Python virtual environment, and the build.

```bash
git clone <this-repo-url> rbitgm
cd rbitgm
chmod +x rbitgm.sh
sudo ./rbitgm.sh
```

### What the installer does

1. Installs system dependencies (SDL2, dev headers, `upx`, `patchelf`)
2. Creates an isolated virtualenv at `~/rabbit_racer_env`
3. Installs `pygame` + `pyinstaller` into it
4. Copies `game.py` and `uninstall.sh` into `~/rabbit_racer`
5. Compiles a standalone binary with PyInstaller (`~/rabbit_racer/bin/rabbit-racer`)
6. Symlinks it to `/usr/local/bin/rabbit-racer`
7. Adds a **Rabbit Racer** entry to your Games menu

Once installed, launch it from the Games menu, or from any terminal:

```bash
rabbit-racer
```

## Uninstalling

The game can also uninstall itself from **inside the game** — click **UNINSTALL** from the pause menu or game-over screen — or manually:

```bash
sudo ~/rabbit_racer/uninstall.sh
```

This removes the install directory, virtualenv, desktop shortcut, system symlink, and saved high score, then deletes itself.

## Project structure

```
rbitgm/
├── rbitgm.sh          # installer — builds & deploys the game
├── uninstall.sh        # standalone uninstaller (also copied into the install dir)
├── game.py              # the game itself (single-file, pygame)
├── README.md
└── LICENSE
```

## Requirements

- Linux (Debian/Ubuntu-based — e.g. Raspberry Pi OS)
- `sudo` access for the installer (system packages + `/usr/local/bin` symlink)
- ~1–3 minutes for the PyInstaller build on a Raspberry Pi

## License

All rights reserved — see [LICENSE](LICENSE). This project's source and assets may **not** be copied, redistributed, or reused without explicit permission from the author.

---

<div align="center">
<sub>Built with 🐇 + 🐕 by Vikalp Sharma</sub>
</div>
