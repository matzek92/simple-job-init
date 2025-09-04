import time
import os
from datetime import datetime

from sji.sji import SimpleJobInit


if __name__ == "__main__":

    sji = SimpleJobInit(__file__)

    logger = sji.logger
    logger.info("Test job started")

    # Create tempfile
    tempfile_path = sji.get_tmp_file_path("test.txt")
    with open(tempfile_path, "w") as f:
        f.write("Tempfile content.")
    logger.info("Tempfile created: {}".format(tempfile_path))
    time.sleep(5)
    os.remove(tempfile_path)
    logger.info("Tempfile deleted: {}".format(tempfile_path))

    # Create persistent file
    persistent_file_path = sji.get_persistent_file_path("txt")
    with open(persistent_file_path, "a") as f:
        f.write(f"Test job started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n")

    logger.info("Persistent file created: {}".format(persistent_file_path))

    logger.info("Test job finished")
