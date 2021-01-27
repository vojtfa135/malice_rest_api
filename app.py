from celery.schedules import crontab
from db import db_init, db_get_entry, db_make_entry, db_make_md5_hash, db_conn, db_make_col, db_delete_entry
import json
from bson import ObjectId
import subprocess
from datetime import datetime
import os

app = Flask(__name__)
celery = Celery("app", backend="redis://redis:6379/0", broker="redis://redis:6379/0")
celery.conf.beat_schedule = {
    # Executes everyday at 12
    'rebuild-av-images-everyday-at-twelve': {
        'task': 'tasks.rebuild_av_images',
        'schedule': crontab(hour=14),
    },
}
celery.conf.timezone = "Europe/Prague"


@app.route("/")
def index():
    return "Upload files to Malice scan, go to /upload"


@app.route("/debug")
def debug():
    md5_hash = "09f7e02f1290be211da707a266f153b3"
    rebuild_av_images.delay()
    return "{}".format(db_delete_entry(md5_hash))


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        to_scan_path = os.path.join(os.getenv("SCAN_DIR"), "malware_file")
        file_to_scan = request.files["file"]
        file_to_scan.save(to_scan_path)
        md5_key = db_make_md5_hash(to_scan_path)
        if bool(db_get_entry(md5_key)):
            return JSONEncoder().encode(db_get_entry(md5_key))
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
        if bool(db_get_entry(request.args["md5_hash"])):
            return JSONEncoder().encode(db_get_entry(request.args["md5_hash"]))
        else:
            return json.dumps({"response": "No entry for {}".format(request.args["md5_hash"])})
    else:
        return json.dumps({"response": "md5_hash param is required, check your request"})


@app.route('/process/<filename>')
def task_processing(filename):
    task = processing.delay(filename)
    async_result = AsyncResult(id=task.task_id, app=celery)
    processing_result = async_result.get()
    return processing_result


@celery.task(name="scan_file")
def scan_file(malware="malware_file"):
    today = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
    scan_dir = os.getenv("SCAN_DIR")
    mount_scan_dir = os.getenv("AV_SCAN_DIR")
    fp = os.path.join(scan_dir, malware)
    container_working_dir = "/malware"
    mount = mount_scan_dir + ":" + container_working_dir
    # antiviruses = ["clamav", "comodo", "escan", "fsecure", "mcafee", "sophos"]
    antiviruses = ["clamav"]
    results = {
            "md5_hash": db_make_md5_hash(fp),
            "scan_date": today,
            "results": {
                        "clamav": {"infected": "", "malware_info": ""},
                        "comodo": {"infected": "", "malware_info": ""},
                        "escan": {"infected": "", "malware_info": ""},
                        "fsecure": {"infected": "", "malware_info": ""},
                        "mcafee": {"infected": "", "malware_info": ""},
                        "sophos": {"infected": "", "malware_info": ""}
                   }
            }

    for antivirus in antiviruses:
        # scan = str(subprocess.run(["docker", "run", "-v", mount, antivirus, malware], stdout=subprocess.PIPE).stdout)
        # scan = scan.strip("b\'").strip("\\n")
        scan = (lambda x: json.loads(x.strip("b\'").strip("\\n")))(str(subprocess.run(["docker", "run", "-v", mount, antivirus, malware], stdout=subprocess.PIPE).stdout))
        results["results"][antivirus]["infected"] = scan["infected"]
        if scan["signature"]:
            results["results"][antivirus]["malware_info"] = scan["signature"]

    db_make_entry(results)


@celery.task(name="rebuild_av_images")
def rebuild_av_images():
    av_image_names = ["clamav"]
    for image_name in av_image_names:
        subprocess.run(["docker", "build", "-t", "{}:latest".format(image_name), "AVs/{}".format(image_name) ], stdout=subprocess.DEVNULL)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


if __name__ == "__main__":
    app.run(host=os.getenv("FLASK_RUN_HOST"), port=os.getenv("FLASK_RUN_PORT"))
