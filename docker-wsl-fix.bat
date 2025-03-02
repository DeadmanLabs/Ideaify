@echo off
wsl --shutdown
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data
wsl --update
