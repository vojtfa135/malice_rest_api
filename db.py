import hashlib
import pathlib
import pymongo


def db_conn():
    return pymongo.MongoClient("mongodb://database:27017")


def db_init(db_name="malware"):
    return db_conn()[db_name]


def db_make_col(col_name="samples"):
    return db_init()[col_name]


def db_make_entry(entry):
    return db_make_col().insert_one(entry)


def db_get_entry(md5_hash):
    query = {"md5_hash": md5_hash}
    return db_make_col().find_one(query)


def db_delete_entry(md5_hash):
    query = {"md5_hash": md5_hash}
    return db_make_col().delete_one(query)


def db_make_md5_hash(fp):
    return hashlib.md5(pathlib.Path(fp).read_bytes()).hexdigest()
