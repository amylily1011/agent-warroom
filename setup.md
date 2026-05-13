# Hackathon Sandbox Setup

Steps to replicate this development environment on a fresh Ubuntu machine.

## Prerequisites

- Ubuntu 22.04+ (tested on 24.04)
- User with `sudo` access (passwordless sudo recommended for automation)

---

## 1. Update apt and install base dependencies

```bash
sudo apt update
sudo apt install -y git curl nodejs npm python3-pip build-essential
```

Installs:
- `git` — version control
- `curl` — used by installers below
- `nodejs` + `npm` — Node.js runtime and package manager
- `python3-pip` — Python package manager
- `build-essential` — C/C++ compiler toolchain (required by Homebrew and Rust crates)

Versions installed on this machine:
- Node.js `v18.19.1`
- npm `9.2.0`
- Python `3.12.3`
- git `2.43.0`

---

## 2. Install Rust (via rustup)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Follow the prompts (default install is fine). Then activate in the current shell:

```bash
source "$HOME/.cargo/env"
```

This is automatically added to `~/.bashrc` and `~/.profile` by the installer.

Versions installed on this machine:
- rustc `1.75.0`
- cargo `1.75.0`

---

## 3. Create the project directory

```bash
mkdir -p ~/hackathon
```

---

## 4. Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After install, add Homebrew to your PATH:

```bash
echo >> ~/.bashrc
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"
```

Verify:

```bash
brew --version
```

Version installed on this machine: `5.1.11`

> **Note:** On Linux, Homebrew installs to `/home/linuxbrew/.linuxbrew` (not `/usr/local` as on macOS).

---

## 5. Reload your shell

For all PATH changes to take effect in your current terminal:

```bash
source ~/.bashrc
```

Or simply open a new terminal session.

---

## Installed tool summary

| Tool | Version | How installed |
|------|---------|---------------|
| git | 2.43.0 | apt |
| Node.js | 18.19.1 | apt |
| npm | 9.2.0 | apt |
| Python | 3.12.3 | apt (system) |
| Rust / cargo | 1.75.0 | rustup |
| Homebrew | 5.1.11 | official install script |
| build-essential | — | apt |
