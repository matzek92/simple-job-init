# SJI

Eine einfache Python-Bibliothek für die Initialisierung von Jobs/Skripten (Logging, Konfiguration, Ordnerstruktur).

## Installation

```bash
pip install sji
```

## Verwendung

```python
from sji import SimpleJobInit

# __file__ an SimpleJobInit übergeben
sji = SimpleJobInit(__file__)

# Logger verwenden
sji.logger.info("Starte Job...")

# Konfiguration lesen (INI)
cfg = sji.config
value = cfg.get('section', 'key', fallback='default')

# Persistente Datei-Pfade erhalten
csv_path = sji.get_persistent_file_path('csv')
```

Dabei werden automatisch erzeugt/genutzt:
- logs/<skriptname>.log (mit optionaler Rotation)
- tmp/ Verzeichnis
- <skriptname>.config.ini für Einstellungen

## Minimalbeispiel für die INI-Datei

Datei: `<skriptname>.config.ini` im selben Verzeichnis wie das Skript

```ini
[logging]
level = INFO
log_rotation_when = midnight
log_rotation_backup_count = 7

[section]
key = some-value
```

## API

### Klasse: SimpleJobInit

- `SimpleJobInit(script_file_path: str)`
  - Initialisiert Logging, lädt/prüft INI-Config, erzeugt Ordner (logs, tmp)
- Eigenschaften
  - `logger`: konfigurierter `logging.Logger`
  - `config`: `configparser.ConfigParser`
- Methoden
  - `get_persistent_file_path(file_ending: str) -> str`: gibt Pfad `<skriptname>.<file_ending>` zurück

## Lizenz

MIT-Lizenz - siehe [LICENSE](LICENSE) für Details.

- Project build with support of AI (Cursor IDE). 