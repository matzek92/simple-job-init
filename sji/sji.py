"""
Einfache Helper-Funktionen für Job-Initialisierung.
"""

from typing import Dict, Any
from datetime import datetime, timezone
import uuid
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import configparser
import hashlib


class SimpleJobInit(object):

    def __init__(self, script_file_path: str):

        self._script_file_path = script_file_path
        self._script_dir = os.path.dirname(script_file_path)
        self._script_basename = os.path.basename(script_file_path).replace(".py", "")
                
        self._log_folder = os.path.join(self._script_dir, "logs")
        if not os.path.exists(self._log_folder):
            os.makedirs(self._log_folder)
        self._log_filepath = os.path.join(self._log_folder, f"{self._script_basename}.log")

        self._config_filepath = os.path.join(self._script_dir, f"{self._script_basename}.config.ini")
        self._config = configparser.ConfigParser()
        if os.path.isfile(self._config_filepath):
            self._config.read(self._config_filepath)
        else:
            raise ValueError("Config file {} missing...".format(self._config_filepath))

        logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s][%(module)s - %(funcName)s] %(message)s')
        self._logger = logging.getLogger(self._script_basename)
        
        if self._config.has_section('logging'):

            logging_config = self._config['logging']
            level = logging_config.get('level', logging.INFO)
            self._logger.setLevel(level)

            log_rotation_when = logging_config.get('log_rotation_when', 'midnight')
            log_rotation_backup_count = int(logging_config.get('log_rotation_backup_count', 0))
            log_file_handler = TimedRotatingFileHandler(self._log_filepath, encoding='utf-8', when=log_rotation_when, backupCount=log_rotation_backup_count)
            log_format = logging_config.get('log_format', '[%(asctime)s][%(levelname)s][%(name)s][%(module)s - %(funcName)s] %(message)s')
            formatter = logging.Formatter(log_format)
            log_file_handler.setFormatter(formatter)
            self._logger.addHandler(log_file_handler)
        
       
        self._tmp_folder = os.path.join(self._script_dir, "tmp")
        if not os.path.exists(self._tmp_folder):
            os.makedirs(self._tmp_folder)
        self._persistent_files_path_stub = os.path.join(self._script_dir, f"{self._script_basename}")

    @property
    def logger(self):
        return self._logger

    @property
    def config(self):
        return self._config

    def get_tmp_file_path(self, file_name: str):
        return os.path.join(self._tmp_folder, file_name)

    def get_persistent_file_path(self, file_ending: str):
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

    def log_config(self, secret_fields=None):
        """Loggt die aktuelle Konfiguration, maskiert angegebene Geheimfelder.

        Args:
            secret_fields: Iterable von Feldnamen (case-insensitive), die maskiert
                           werden sollen; gilt für alle Sections.
        """
    
        secret_set = {str(name).lower() for name in (secret_fields or [])}

        self._logger.info("Konfiguration (maskiert):")
        for section in sorted(self._config.sections()):
            self._logger.info(f"[{section}]")
            for key, value in sorted(self._config.items(section)):
                display_value = '********' if key.lower() in secret_set else value.strip()
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
