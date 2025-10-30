import time
import os
from datetime import datetime

from sji.sji import SimpleJobInit


if __name__ == "__main__":

    sji = SimpleJobInit(__file__)

    logger = sji.logger
    logger.info("Test job started")
    
    # Basic SJI API checks and info output
    try:
        job_version = sji.get_job_script_version(include_git_tag=True)
        cfg_hash = sji.get_config_file_hash()
        cfg_version = sji.get_config_file_version()
        logger.info(f"job_version={job_version}")
        logger.info(f"config_hash={cfg_hash}")
        logger.info(f"config_version={cfg_version}")
        # Log configuration with masking
        sji.log_config(secret_fields=["password", "db_password", "api_key", "token"]) 
        sji.log_config() 
    except Exception as exc:
        logger.error(f"SJI API check failed: {exc}")
        raise

    # Create tempfile
    tempfile_path = sji.get_tmp_file_path("test.txt")
    with open(tempfile_path, "w") as f:
        f.write("Tempfile content.")
    logger.info("Tempfile created: {}".format(tempfile_path))
    time.sleep(1)
    os.remove(tempfile_path)
    logger.info("Tempfile deleted: {}".format(tempfile_path))

    # Create persistent file
    persistent_file_path = sji.get_persistent_file_path("txt")
    with open(persistent_file_path, "a") as f:
        f.write(f"Test job started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n")

    logger.info("Persistent file created: {}".format(persistent_file_path))

    logger.info("Test job finished")
