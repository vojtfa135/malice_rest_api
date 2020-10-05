import subprocess
import os
import json
import hashlib
import pathlib


def db_init(db_path="/var/www/db/"):
    db = str(subprocess.run(["ls", db_path], stdout=subprocess.PIPE).stdout)
    db = db.strip("b'").split("\\n")
    db.remove("")
    return (db, db_path)


def db_get_entry(entry):
    with open(os.path.join(db_init()[1], entry), "r") as db_entry:
        db_dump = db_entry.read()
        return json.dumps(db_dump)


def db_make_entry(fp, content):
    key = db_make_md5_hash(fp)
    with open(os.path.join(db_init()[1], key), "w") as db_entry:
        db_dump = db_entry.write(content)


def db_make_md5_hash(fp):
    return hashlib.md5(pathlib.Path(fp).read_bytes()).hexdigest()
