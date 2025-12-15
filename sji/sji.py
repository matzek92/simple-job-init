"""
Einfache Helper-Funktionen für Job-Initialisierung.
"""

from datetime import datetime, timezone
import os
import re
import logging
from logging.handlers import TimedRotatingFileHandler
import configparser
import hashlib
from typing import Iterable, Mapping, Dict, Set


class SimpleJobInit(object):

    def __init__(self, script_file_path: str):

        self._script_file_path = script_file_path
        self._script_dir = os.path.dirname(script_file_path)
        self._script_basename = os.path.basename(script_file_path).replace(".py", "")
        
        # Initialize persistent files path stub early (needed for credential resolution)
        self._persistent_files_path_stub = os.path.join(self._script_dir, f"{self._script_basename}")
        
        # Track fields that were replaced with credentials (for automatic masking in logs)
        # Dict[section_lower, Set[field_lower]]
        self._credential_replaced_fields: Dict[str, Set[str]] = {}
                
        self._log_folder = os.path.join(self._script_dir, "logs")
        if not os.path.exists(self._log_folder):
            os.makedirs(self._log_folder)
        self._log_filepath = os.path.join(self._log_folder, f"{self._script_basename}.log")

        self._config_filepath = os.path.join(self._script_dir, f"{self._script_basename}.config.ini")
        self._config = configparser.ConfigParser()
        if os.path.isfile(self._config_filepath):
            try:
                self._config.read(self._config_filepath)
            except (configparser.Error, OSError) as exc:
                raise ValueError(f"Config file {self._config_filepath} could not be read: {exc}") from exc
        else:
            raise ValueError("Config file {} missing...".format(self._config_filepath))
        
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s][%(module)s - %(funcName)s] %(message)s')

        self._logger = logging.getLogger(self._script_basename)
        self._logger.setLevel(logging.INFO)
        
        if self._config.has_section('logging'):

            logging_config = self._config['logging']
            level = logging_config.get('level', logging.INFO)
            self._logger.setLevel(level)

            log_rotation_when = logging_config.get('log_rotation_when', 'midnight')
            log_rotation_backup_count = int(logging_config.get('log_rotation_backup_count', 0))
            log_file_handler_exists = any(
                isinstance(h, TimedRotatingFileHandler) and getattr(h, "baseFilename", None) == self._log_filepath
                for h in self._logger.handlers
            )
            log_format = logging_config.get('log_format', '[%(asctime)s][%(levelname)s][%(name)s][%(module)s - %(funcName)s] %(message)s')
            formatter = logging.Formatter(log_format)

            if not log_file_handler_exists:
                log_file_handler = TimedRotatingFileHandler(
                    self._log_filepath,
                    encoding='utf-8',
                    when=log_rotation_when,
                    backupCount=log_rotation_backup_count
                )
                log_file_handler.setFormatter(formatter)
                self._logger.addHandler(log_file_handler)

            # Optional: zusätzlicher Console-Handler
            if logging_config.getboolean('console', False):
                console_exists = any(isinstance(h, logging.StreamHandler) and not isinstance(h, TimedRotatingFileHandler) for h in self._logger.handlers)
                if not console_exists:
                    console_handler = logging.StreamHandler()
                    console_handler.setFormatter(formatter)
                    self._logger.addHandler(console_handler)

            # Propagation steuern
            self._logger.propagate = logging_config.getboolean('propagate', False)
        
        self._tmp_folder = os.path.join(self._script_dir, "tmp")
        if not os.path.exists(self._tmp_folder):
            os.makedirs(self._tmp_folder)
        
        self._resolve_credential_placeholders()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def config(self) -> configparser.ConfigParser:
        return self._config

    def get_tmp_file_path(self, file_name: str) -> str:
        return os.path.join(self._tmp_folder, file_name)

    def get_persistent_file_path(self, file_ending: str) -> str:
        return f"{self._persistent_files_path_stub}.{file_ending}"

    def get_job_script_version(self, include_git_tag: bool = False):
        return get_script_version(self._script_file_path, include_git_tag)

    def get_config_file_hash(self) -> str:
        """Berechne den SHA-256-Dateihash der Konfigurationsdatei (Binärinhalt)."""
        hasher = hashlib.sha256()
        with open(self._config_filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _resolve_credential_placeholders(self):
        """Ersetzt Platzhalter [[[[name]]]] in der Konfiguration mit Werten aus credentials.ini.
        
        Die Platzhalter werden durch Werte aus derselben Section und mit demselben Key-Namen
        aus der credentials.ini-Datei ersetzt. Wenn credentials.ini nicht existiert oder
        ein Platzhalter nicht gefunden wird, bleibt der Platzhalter unverändert.
        
        Felder, die durch Credentials ersetzt wurden, werden für automatische Maskierung
        in log_config() gespeichert.
        """

        credentials_filepath = self.get_persistent_file_path("credentials.ini")

        if not os.path.isfile(credentials_filepath):
            self._logger.warning("Credentials file %s missing; placeholders remain unresolved.", credentials_filepath)
            return
        
        credentials = configparser.ConfigParser()
        try:
            read_files = credentials.read(credentials_filepath)
        except (configparser.Error, OSError) as exc:
            raise ValueError(f"Credentials file {credentials_filepath} could not be read: {exc}") from exc

        if not read_files:
            self._logger.warning("Credentials file %s could not be read; placeholders remain unresolved.", credentials_filepath)
            return
        
        # Pattern für Platzhalter: [[[[name]]]]
        placeholder_pattern = re.compile(r'\[\[\[\[([A-Za-z0-9_]+)\]\]\]\]')

        replaced_fields = []
        missing_placeholders = []
        
        # Durch alle Sections und Keys iterieren
        for section in self._config.sections():
            section_has_placeholder = False
            if not credentials.has_section(section):
                # Nur warnen, wenn Platzhalter vorhanden wären
                for key in self._config[section]:
                    if placeholder_pattern.search(self._config[section][key]):
                        section_has_placeholder = True
                        break
                if section_has_placeholder:
                    self._logger.warning("Credentials section [%s] missing for placeholder resolution.", section)
                continue
            
            for key in self._config[section]:
                value = self._config[section][key]
                
                # Prüfe, ob der Wert Platzhalter enthält
                has_placeholder = bool(placeholder_pattern.search(value))
                
                # Suche nach Platzhaltern im Wert
                def replace_placeholder(match):
                    placeholder_key = match.group(1)
                    # Suche in derselben Section nach dem Key
                    if credentials.has_option(section, placeholder_key):
                        replaced_fields.append((section, key, placeholder_key))
                        return credentials.get(section, placeholder_key)
                    # Wenn nicht gefunden, Platzhalter unverändert lassen und merken
                    missing_placeholders.append((section, placeholder_key))
                    return match.group(0)
                
                # Ersetze alle Platzhalter im Wert
                resolved_value = placeholder_pattern.sub(replace_placeholder, value)
                
                # Wenn Platzhalter vorhanden waren und der Wert sich geändert hat, Feld merken
                if has_placeholder and resolved_value != value:
                    self._credential_replaced_fields.setdefault(section.lower(), set()).add(key.lower())
                
                self._config.set(section, key, resolved_value)

        if replaced_fields:
            self._logger.info(
                "Replaced credential placeholders for: %s",
                ", ".join(f"[{s}].{k}" for s, k, _ in replaced_fields)
            )

        if missing_placeholders:
            # Deduplicate warnings
            missing_seen = {(s.lower(), k.lower()) for s, k in missing_placeholders}
            for section_lower, key_lower in sorted(missing_seen):
                self._logger.warning("Credential placeholder missing value: [%s].%s", section_lower, key_lower)

    @property
    def credentials(self) -> configparser.ConfigParser:
        
        credentials_filepath = self.get_persistent_file_path("credentials.ini")
        if not os.path.isfile(credentials_filepath):
            raise ValueError("Credentials file {} missing...".format(credentials_filepath))
        credentials = configparser.ConfigParser()
        try:
            read_files = credentials.read(credentials_filepath)
        except (configparser.Error, OSError) as exc:
            raise ValueError(f"Credentials file {credentials_filepath} could not be read: {exc}") from exc
        if not read_files:
            raise ValueError("Credentials file {} could not be read...".format(credentials_filepath))
        return credentials

    def get_config_file_version(self) -> str:
        """Kombiniert den Konfigurations-Hash mit dem letzten Änderungszeitpunkt der INI-Datei.

        Format: "cfg_<YYYY-MM-DD_HH:MM:SS>_<sha256>" (Zeit in UTC)
        """
        last_modification_timestamp = os.path.getmtime(self._config_filepath)
        formatted_timestamp = datetime.fromtimestamp(
            last_modification_timestamp, tz=timezone.utc
        ).strftime('%Y-%m-%d_%H:%M:%S')
        cfg_hash = self.get_config_file_hash()  
        return f"cfg_{formatted_timestamp}_{cfg_hash}"

    def log_config(self, secret_fields: Mapping[str, Iterable[str]] | None = None):
        """Loggt die aktuelle Konfiguration, maskiert angegebene Geheimfelder.

        Felder, die durch Credentials ersetzt wurden, werden automatisch maskiert.

        Args:
            secret_fields: Mapping mit Section-Namen als Keys (case-insensitive)
                           und Iterables von Feldnamen als Values (case-insensitive),
                           die zusätzlich maskiert werden sollen.
                           Beispiel: {'database': ['password', 'user'], 'api': ['api_key']}
        """
    
        # Default-Masken aus Credential-Ersetzungen kopieren
        secret_dict: Dict[str, Set[str]] = {
            section: fields.copy() for section, fields in self._credential_replaced_fields.items()
        }

        config_sections = {section.lower() for section in self._config.sections()}

        if secret_fields:
            if not isinstance(secret_fields, Mapping):
                raise TypeError("secret_fields muss ein Mapping sein: {section: [field1, field2, ...]}")
            
            for section, fields in secret_fields.items():
                section_lower = str(section).lower()
                if isinstance(fields, str):
                    fields_iterable = [fields]
                else:
                    try:
                        fields_iterable = list(fields)
                    except TypeError as exc:
                        raise TypeError("secret_fields values müssen iterierbar sein (z.B. Liste).") from exc

                field_set = {str(field).lower() for field in fields_iterable}
                secret_dict.setdefault(section_lower, set()).update(field_set)

                if section_lower not in config_sections:
                    self._logger.warning("secret_fields section '%s' not present in config.", section)

        self._logger.info("Konfiguration (maskiert):")
        for section in sorted(self._config.sections()):
            self._logger.info(f"[{section}]")
            for key, value in sorted(self._config.items(section)):
                section_lower = section.lower()
                key_lower = key.lower()
                
                # Prüfe ob Feld automatisch oder manuell maskiert werden soll
                section_mask = secret_dict.get(section_lower, set())
                is_masked = key_lower in section_mask
                
                display_value = '********' if is_masked else value.strip()
                self._logger.info(f"{key} = {display_value}")

    def get_postgres_sqlalchemy_engine(self, db_config: configparser.ConfigParser):
        from sqlalchemy import create_engine
        from urllib.parse import quote_plus
        connection_string = 'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'.format(
                db_user=db_config['db_user'],
                db_password=quote_plus(db_config['db_password']),
                db_host=db_config['db_host'],
                db_port=int(db_config['db_port']),
                db_name=db_config['db_name']
        )
        return create_engine(connection_string,
            connect_args={
                'application_name': f'python-{self._script_basename}'
            }
        )

def get_script_version(script_file_path: str, include_git_tag: bool = False) -> str:
    """Erzeuge eine Versionszeichenkette für das Skript.

    Bevorzugt Git-Informationen (über GitPython), andernfalls Fallback auf
    Dateimodifikationszeitpunkt und MD5-Hash des Skriptes.
    
    Args:
        script_file_path: Pfad zum Skript
        include_git_tag: Ob Git-Tag in der Version enthalten sein soll (optional)
    
    Returns:
        - In einem Git-Repo: '<short_sha>[-dirty]' oder mit Tag '<tag>-<short_sha>[-dirty]'
        - Nicht im Repo: '<mtime>.<md5>'
    """
    try:
        # Import hier, damit GitPython nur benötigt wird, wenn verfügbar
        from git import Repo, InvalidGitRepositoryError, NoSuchPathError

        script_dir = os.path.dirname(os.path.abspath(script_file_path))
        repo = None
        try:
            repo = Repo(script_dir, search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError):
            repo = None

        if repo is not None and not repo.bare:
            head_commit = repo.head.commit
            short_sha = head_commit.hexsha[:8]
            dirty = repo.is_dirty(untracked_files=True)

            if include_git_tag:
                # Versuche, den nächsten/aktuellen Tag zu ermitteln
                tag_name = None
                try:
                    # 'git describe --tags --abbrev=0' Äquivalent
                    tag_name = repo.git.describe('--tags', '--abbrev=0')
                except Exception:
                    tag_name = None
                
                base = f"{tag_name}-{short_sha}" if tag_name else short_sha
            else:
                base = short_sha
            
            return f"git_{base}_dirty" if dirty else f"git_{base}"

    except Exception:
        # Falls GitPython nicht installiert oder ein anderer Fehler auftrat, gehe zum Fallback
        pass

    # Fallback: mtime + md5
    last_modification_timestamp = os.path.getmtime(script_file_path)
    formatted_timestamp = datetime.fromtimestamp(last_modification_timestamp, tz=timezone.utc).strftime('%Y-%m-%d_%H:%M:%S')
    with open(script_file_path, "rb") as f:
        md5_hash = hashlib.md5(f.read()).hexdigest()
    return f"stats_{formatted_timestamp}_{md5_hash}"
