# SJI

Eine einfache Python-Bibliothek für die Initialisierung von Jobs/Skripten (Logging, Konfiguration, Ordnerstruktur).

## Installation

```bash
pip install sji
```

## Verwendung

```python
from sji import SimpleJobInit, get_script_version

# __file__ an SimpleJobInit übergeben
sji = SimpleJobInit(__file__)

# Logger verwenden
sji.logger.info("Starte Job...")

# Konfiguration lesen (INI)
cfg = sji.config
value = cfg.get('section', 'key', fallback='default')

# Persistente Datei-Pfade erhalten
csv_path = sji.get_persistent_file_path('csv')

# Temporäre Datei-Pfade erhalten
tmp_path = sji.get_tmp_file_path('work.tmp')

# Versionen ermitteln
sji.logger.info(f"script_version={sji.get_job_script_version(include_git_tag=True)}")
sji.logger.info(f"config_file_hash={sji.get_config_file_hash()}")
sji.logger.info(f"config_file_version={sji.get_config_file_version()}")

# Top-Level-Funktion (unabhängig von der Klasse):
script_version = get_script_version(__file__, include_git_tag=True)

# Konfiguration mit Maskierung loggen
sji.log_config(secret_fields=["password", "db_password", "api_key", "token"]) 
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

## Credential-Ersetzung

SJI unterstützt die automatische Ersetzung von Platzhaltern in der Konfigurationsdatei durch Werte aus einer separaten `credentials.ini`-Datei.
Dies ermöglicht es, sensible Daten wie Passwörter oder API-Schlüssel getrennt von der Hauptkonfiguration zu verwalten.

### Funktionsweise

1. **Platzhalter-Format**: In der `config.ini` können Platzhalter im Format `[[[[name]]]]` verwendet werden.
2. **Credentials-Datei**: Die Datei `<skriptname>.credentials.ini` wird automatisch im selben Verzeichnis wie das Skript gesucht.
3. **Ersetzung**: Platzhalter werden durch Werte aus derselben Section und mit demselben Key-Namen aus der `credentials.ini` ersetzt.
4. **Optional**: Wenn die `credentials.ini` nicht existiert, bleiben die Platzhalter unverändert.

### Beispiel

**`test_job.config.ini`:**
```ini
[db_config]
db_user = postgres
db_password = [[[[db_password]]]]
db_host = localhost
db_port = 5432
db_name = test_db

[api]
api_key = [[[[api_key]]]]
```

**`test_job.credentials.ini`:**
```ini
[db_config]
db_password = my_secret_password_123

[api]
api_key = api_key_abc123xyz
```

Nach der Initialisierung von `SimpleJobInit` werden die Platzhalter automatisch ersetzt:
- `db_password` wird zu `my_secret_password_123`
- `api_key` wird zu `api_key_abc123xyz`

### Hinweise

- Die `credentials.ini` sollte **nicht** in Versionskontrolle (Git) eingecheckt werden
- Platzhalter können nur durch Werte aus derselben Section ersetzt werden
- Wenn ein Platzhalter nicht in der `credentials.ini` gefunden wird, bleibt er unverändert
- Die Ersetzung erfolgt automatisch beim Laden der Konfiguration

## API

### Klasse: SimpleJobInit

- `SimpleJobInit(script_file_path: str)`
  - Initialisiert Logging, lädt/prüft INI-Config, erzeugt Ordner (logs, tmp)
- Eigenschaften
  - `logger`: konfigurierter `logging.Logger`
  - `config`: `configparser.ConfigParser`
- Methoden
  - `get_tmp_file_path(file_name: str) -> str`: Pfad im `tmp/`-Verzeichnis
  - `get_persistent_file_path(file_ending: str) -> str`: Pfad `<skriptname>.<file_ending>`
  - `get_job_script_version(include_git_tag: bool = False) -> str`: ermittelt Skriptversion (Git/FS)
  - `get_config_file_hash() -> str`: SHA-256 Hash der INI-Datei
  - `get_config_file_version() -> str`: `cfg_<UTC-Zeit>_<sha256>` basierend auf Datei-mtime und Hash
  - `log_config(secret_fields) -> None`: loggt INI-Inhalt, maskiert definierte Felder (case-insensitive)
  - `get_postgres_sqlalchemy_engine(db_config)`: baut SQLAlchemy-Engine aus INI-Werten

### Top-Level-Funktion

- `get_script_version(script_file_path: str, include_git_tag: bool = False) -> str`
  - Wie `get_job_script_version`, aber als freie Funktion für eigenständige Nutzung

## Lizenz

MIT-Lizenz - siehe [LICENSE](LICENSE) für Details.

- Project build with support of AI (Cursor IDE). 