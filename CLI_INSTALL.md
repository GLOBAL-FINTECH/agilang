# AGILANG CLI Installers

This folder includes automatic installers for the AGILANG CLI on Windows,
Linux, and macOS. The installers install the package from this folder and
verify both commands:

```text
agilang --version
agi --version
```

## Windows

From PowerShell in the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\installer.ps1
```

Or from PowerShell in the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\install_windows.ps1
```

## Linux

From a terminal in the project root:

```sh
sh scripts/install_linux.sh
```

## macOS

From Terminal in the project root:

```sh
sh scripts/install_macos.sh
```

## Universal Python Installer

You can also run the cross-platform installer directly:

```sh
python install.py
```

Use `python3 install.py` if your system uses `python3` for Python 3.

## Device and OS-specific installs

For Windows, WSL, macOS, Linux, ChromeOS, Android, iOS/iPadOS, Raspberry Pi, Docker, and shared-hosting guidance, see:

```text
DEVICE_OS_INSTALLATION.md
```
