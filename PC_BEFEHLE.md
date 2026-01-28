# More Commands:
git pull
sudo podman-compose down --volumes
sudo podman-compose -f podman-compose.yml up -d --build

# Cleanup: 

The Bomb: podman-compose down --volumes --images all
The Nuke: podman system prune -a --volumes --force

Alle Container stoppen und entfernen: sudo podman rm -af

Alle ungenutzten Netzwerke entfernen: sudo podman network prune -f

Volumes entfernen (da du --volumes genutzt hast): sudo podman volume prune -f