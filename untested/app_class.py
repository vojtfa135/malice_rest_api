from flask import Flask, request
from celery import Celery
from celery_init import make_celery
from db import DB
import json
import subprocess
from datetime import datetime
import os


app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)
celery = make_celery(app)


class App():
  def __init__(self, root_route, upload_route, api_route, http_methods, scan_path, db):
    self.db = db
    self.root_route = "/"
    self.upload_route = os.path.join(self.root_route, "upload")
    self.api_route = os.path.join(self.root_route, "api")
    self.http_methods = ["GET", "POST"]
    self.scan_path = "/var/www/scans/"

  @app.route(self.root_route)
  def index(self):
      return "Upload files to Malice scan, go to /upload"

  @app.route(self.api_route, methods=self.http_methods)
  def upload_file(self):
      if request.method == "POST":
          file_to_scan = request.files["file"]
          file_to_scan.save(os.path.join(self.scan_path, "malware_file"))
          md5_key = self.db.db_make_md5_hash(os.path.join(self.scan_path, "malware_file"))
          if self.db.db_init()[0] != []:
              if md5_key in self.db.db_init()[0]:
                  return self.db.db_get_entry(md5_key)
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

  @app.route(self.api_route, methods=self.methods)
  def get_json(self):
      if "md5_hash" in request.args:
          if request.args["md5_hash"] in self.db.db_init()[0]:
              return self.db.db_get_entry(request.args["md5_hash"])
          else:
              return json.dumps({"response": "No entry for {}".format(request.args["md5_hash"])})
      else:
          return json.dumps({"response": "md5_hash param is required, check your request"})
   
  @celery.task()
  def scan_file(self, malware="malware_file"):
      today = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
      scan_dir = self.scan_path
      fp = os.path.join(scan_dir, malware)
      container_working_dir = "/malware"
      mount = scan_dir + ":" + container_working_dir
      antiviruses = ["clamav", "comodo", "escan", "fsecure", "mcafee", "sophos"]
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
          scan = str(subprocess.run(["docker", "run", "-v", mount, antivirus, malware], stdout=subprocess.PIPE).stdout)
          scan = scan.strip("b\'").strip("\\n")
          scan_dict = json.loads(scan)
          results["results"][antivirus]["infected"] = scan_dict[antivirus]["infected"]
          if scan_dict[antivirus]["result"] != "":
              results["results"][antivirus]["malware_info"] = scan_dict[antivirus]["result"]

      json_results = json.dumps(results)
      self.db.db_make_entry(fp, json_results)


def main():
  db = DB()
  this_app = App(db)
  this_app.index()
  this_app.upload_file()
  this_app.get_json()


if __name__ == "__main__":
  main()
