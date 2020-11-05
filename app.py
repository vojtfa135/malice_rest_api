from flask import Flask, request
from celery import Celery
from celery_init import make_celery
from db import db_init, db_get_entry, db_make_entry, db_make_md5_hash
import json
import subprocess
from datetime import datetime
import os


app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://redis:6379',
    CELERY_RESULT_BACKEND='redis://redis:6379'
)
celery = make_celery(app)


@app.route("/")
def index():
    return "Upload files to Malice scan, go to /upload"


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file_to_scan = request.files["file"]
        file_to_scan.save("/var/www/scans/malware_file")
        md5_key = db_make_md5_hash("/var/www/scans/malware_file")
        if db_init()[0] != []:
            if md5_key in db_init()[0]:
                return db_get_entry(md5_key)
            else:
                scan_file.delay()
                return json.dumps({"to_scan": md5_key})
        else:
            scan_file.delay()
            return json.dumps({"to_scan": md5_key})

    return """
    <!doctype html>
    <title>Upload file</title>
    <h1>Upload a file for scanning</h1>
    <form method=post enctype=multipart/form-data>
    <input type=file name=file>
    <input type=submit value=Upload>
    </form>
    """


@app.route("/api", methods=["GET", "POST"])
def get_json():
    if "md5_hash" in request.args:
        if request.args["md5_hash"] in db_init()[0]:
            return db_get_entry(request.args["md5_hash"])
        else:
            return json.dumps({"response": "No entry for {}".format(request.args["md5_hash"])})
    else:
        return json.dumps({"response": "md5_hash param is required, check your request"})
   

@celery.task()
def scan_file(malware="malware_file"):
    today = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
    scan_dir = "/var/www/scans/"
    fp = os.path.join(scan_dir, malware)
    container_working_dir = os.path.join("/malware", malware)
    mount = scan_dir + ":" + container_working_dir
    # antiviruses = ["clamav", "comodo", "escan", "fsecure", "mcafee", "sophos"]
    antiviruses = ["comodo", "escan", "fsecure"]
    results = {
            "md5_hash": db_make_md5_hash(fp),
            "scan_date": today,
            "results": {
                        "comodo": {"infected": "", "malware_info": ""},
                        "escan": {"infected": "", "malware_info": ""},
                        "fsecure": {"infected": "", "malware_info": ""}
                   }
            }

                        # "clamav": {"infected": "", "malware_info": ""},
                        # "comodo": {"infected": "", "malware_info": ""},
                        # "escan": {"infected": "", "malware_info": ""},
                        # "fsecure": {"infected": "", "malware_info": ""},
                        # "mcafee": {"infected": "", "malware_info": ""},
                        # "sophos": {"infected": "", "malware_info": ""}

    for antivirus in antiviruses:
        scan = str(subprocess.run(["docker", "run", "-v", mount, antivirus, malware], stdout=subprocess.PIPE).stdout)
        scan = scan.strip("b\'").strip("\\n")
        scan_dict = json.loads(scan)
        results["results"][antivirus]["infected"] = scan_dict[antivirus]["infected"]
        if scan_dict[antivirus]["result"] != "":
            results["results"][antivirus]["malware_info"] = scan_dict[antivirus]["result"]
    
    json_results = json.dumps(results)
    db_make_entry(fp, json_results)
