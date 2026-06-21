# AGILANG Device and OS Installation Guide

This guide explains how to install and verify AGILANG on common desktop, server, mobile, and development-device environments.

## Quick Requirements

- Python 3.10 or newer
- `pip`
- Git, when installing from a repository checkout
- A terminal with permission to install Python packages

Verify Python first:

```sh
python --version
python -m pip --version
```

If your platform uses `python3`, replace `python` with `python3`.

## Windows 10/11

Use PowerShell from the AGILANG source folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
python -m pip install --upgrade pip
python -m pip install -e .
agi --version
agilang --version
```

Or run the bundled installer:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\install_windows.ps1
```

Run an app:

```powershell
agi serve src\main.agi --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

## Windows with WSL

Install Ubuntu or another WSL distribution, then run the Linux steps inside the WSL terminal:

```sh
sudo apt update
sudo apt install -y python3 python3-pip git
python3 -m pip install --upgrade pip
python3 -m pip install -e .
agi --version
```

Use WSL when you want Linux-like shell behavior, deployment parity, or Unix scripts on a Windows device.

## macOS Intel and Apple Silicon

Install Python from Python.org, Homebrew, or your organization-managed package source.

Homebrew example:

```sh
brew install python git
python3 -m pip install --upgrade pip
python3 -m pip install -e .
agi --version
agilang --version
```

Or run:

```sh
sh scripts/install_macos.sh
```

Apple Silicon and Intel Macs use the same Python install flow. Native prebuilt runtime files, when present, are separated under:

```text
native/prebuilt/macos-arm64/
native/prebuilt/macos-x86_64/
```

## Linux Desktop and Server

Debian or Ubuntu:

```sh
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
python3 -m pip install --upgrade pip
python3 -m pip install -e .
agi --version
```

Fedora:

```sh
sudo dnf install -y python3 python3-pip git
python3 -m pip install --upgrade pip
python3 -m pip install -e .
agi --version
```

Arch Linux:

```sh
sudo pacman -Syu python python-pip git
python -m pip install --upgrade pip
python -m pip install -e .
agi --version
```

Or use the Linux installer:

```sh
sh scripts/install_linux.sh
```

For Linux servers, run AGILANG behind a reverse proxy such as NGINX or Caddy. See:

```text
deployment/NGINX.md
deployment/CADDY.md
```

## ChromeOS

Enable the Linux development environment, then use the Debian/Ubuntu Linux commands:

```sh
sudo apt update
sudo apt install -y python3 python3-pip git
python3 -m pip install -e .
agi --version
```

ChromeOS is best for development and testing. Production hosting should use a Linux server or managed hosting environment.

## Android

Android support is intended for development, experiments, and native/mobile integration work.

### Termux Development Install

Install Termux from F-Droid, then run:

```sh
pkg update
pkg install python git clang
python -m pip install --upgrade pip
python -m pip install -e .
agi --version
```

Run local examples from the AGILANG source folder:

```sh
agi run examples/hello.agi
```

### Android Native Runtime Assets

Prebuilt runtime folders, when available, are organized by ABI:

```text
native/prebuilt/android-arm64-v8a/
native/prebuilt/android-x86_64/
```

Use `android-arm64-v8a` for most modern Android phones. Use `android-x86_64` for emulators or x86_64 Android devices.

## iPhone and iPad

iOS and iPadOS do not provide a normal unrestricted system Python environment. Use one of these options:

- Develop AGILANG projects on macOS, Windows, or Linux, then expose the app over a local network or hosted server.
- Use a Python-capable iOS app for lightweight script experiments.
- Use the iOS native runtime assets from a host build process when integrating with an iOS app.

Prebuilt runtime folders, when available:

```text
native/prebuilt/ios-arm64/
native/prebuilt/ios-simulator-arm64/
native/prebuilt/ios-simulator-x86_64/
```

Use `ios-arm64` for physical devices. Use simulator folders for Xcode simulator targets.

## Raspberry Pi and ARM Linux

Install Python and Git using your distribution package manager:

```sh
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
python3 -m pip install --upgrade pip
python3 -m pip install -e .
agi --version
```

If native prebuilt binaries are not supplied for the device architecture, build from source or run in Python-only mode.

## Docker or Containers

Use a Python base image:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN python -m pip install --upgrade pip && python -m pip install -e .
EXPOSE 8000
CMD ["agi", "serve", "src/main.agi", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```sh
docker build -t agilang-app .
docker run --rm -p 8000:8000 agilang-app
```

## Shared Hosting, cPanel, and Plesk

Use the CGI/FastCGI deployment files when Python app hosting is available:

```text
public_html/app.cgi
public_html/app.fcgi
passenger_wsgi.py
```

See:

```text
docs/CPANEL_PLESK_CGI_FASTCGI.md
```

## Verify Every Install

Run:

```sh
agi --version
agilang --version
agi run examples/hello.agi
```

For a web app:

```sh
agi serve src/main.agi --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/
```

## Troubleshooting

If `agi` is not found, restart the terminal and check the Python scripts path.

Windows commonly uses:

```text
%APPDATA%\Python\Python312\Scripts
```

Linux and macOS commonly use:

```text
~/.local/bin
```

If package installation fails, upgrade packaging tools:

```sh
python -m pip install --upgrade pip setuptools wheel
```

If a port is already in use, choose another port:

```sh
agi serve src/main.agi --host 127.0.0.1 --port 8001
```

If native runtime files are missing for your device, use Python-only mode or build the native runtime for that platform.
