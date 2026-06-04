# python_automation_tools.py  — all-in-one automation reference
# Run any section directly; comment out the ones you don't need.
# pip install watchdog requests beautifulsoup4 schedule apscheduler python-crontab

import os, shutil, time, csv, smtplib, argparse, subprocess
from pathlib   import Path
from datetime  import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders

# ── 1. ARGPARSE — CLI argument parsing ───────────────────────────────────────
def make_parser():
    p = argparse.ArgumentParser(description="File organiser CLI")
    p.add_argument("folder",     type=Path,        help="Target folder")
    p.add_argument("--ext",      nargs="+",         default=[".pdf",".jpg",".csv"])
    p.add_argument("--verbose",  action="store_true")
    p.add_argument("--workers",  type=int,          default=4, choices=range(1,9), metavar="[1-8]")
    return p

# ── 2. FILE ORGANISER — shutil ────────────────────────────────────────────────
EXT_MAP = {".pdf":"PDFs",".jpg":"Images",".png":"Images",
           ".csv":"Data",".xlsx":"Data",".mp4":"Videos"}

def organise(folder: str):
    src = Path(folder)
    for f in src.iterdir():
        if f.is_file():
            dest = src / EXT_MAP.get(f.suffix, "Other")
            dest.mkdir(exist_ok=True)
            shutil.move(str(f), dest / f.name)
            print(f"Moved {f.name} → {dest.name}/")

# ── 3. WATCHDOG — real-time folder watcher ────────────────────────────────────
from watchdog.observers import Observer
from watchdog.events    import FileSystemEventHandler

class AutoOrganiser(FileSystemEventHandler):
    def __init__(self, folder): self.folder = folder
    def on_created(self, event):
        if not event.is_directory:
            f    = Path(event.src_path)
            dest = Path(self.folder) / EXT_MAP.get(f.suffix, "Other")
            dest.mkdir(exist_ok=True)
            shutil.move(str(f), dest / f.name)
            print(f"Auto-moved {f.name}")

def watch_folder(folder: str):
    obs = Observer()
    obs.schedule(AutoOrganiser(folder), folder, recursive=False)
    obs.start()
    print(f"Watching {folder} ... (Ctrl+C to stop)")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()

# ── 4. BEAUTIFULSOUP — web scraping ───────────────────────────────────────────
import requests
from bs4 import BeautifulSoup

def scrape_quotes() -> list:
    r    = requests.get("https://quotes.toscrape.com", timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    return [
        {"text":   q.find("span", class_="text").text,
         "author": q.find("small").text,
         "tags":   [t.text for t in q.select(".tag")],
         "scraped_at": datetime.now().isoformat()}
        for q in soup.select(".quote")[:5]
    ]

def save_csv(rows, path="quotes.csv"):
    with open(path, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=["text","author","tags","scraped_at"]).writerows(rows)

# ── 5. SMTP — send email alerts ───────────────────────────────────────────────
def send_alert(subject, body, to, gmail_user, app_pw, attachment=None):
    msg = MIMEMultipart()
    msg["Subject"], msg["From"], msg["To"] = subject, gmail_user, to
    msg.attach(MIMEText(body, "plain"))
    if attachment:
        with open(attachment, "rb") as fh:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(fh.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={attachment}")
        msg.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(gmail_user, app_pw)
        s.send_message(msg)
    print("Alert sent ✓")

# ── 6. SCHEDULE — simple in-process scheduler ────────────────────────────────
import schedule

def run_schedule_demo():
    def job(): print(f"[{datetime.now():%H:%M:%S}] scraping...")
    schedule.every(10).seconds.do(job)
    schedule.every().day.at("08:00").do(lambda: print("Daily report"))
    deadline = time.time() + 35
    while time.time() < deadline:
        schedule.run_pending()
        time.sleep(1)

# ── 7. APSCHEDULER — advanced background scheduler ────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron         import CronTrigger

def run_apscheduler_demo():
    def scrape_job(): print(f"[{datetime.now():%H:%M:%S}] APScheduler scrape")
    def report_job(): print(f"[{datetime.now():%H:%M:%S}] APScheduler report")

    sched = BackgroundScheduler()
    sched.add_job(scrape_job, "interval", seconds=15,  id="scraper")
    sched.add_job(report_job, CronTrigger(day_of_week="mon-fri", hour=7, minute=30),
                  id="daily_report")
    sched.start()
    for job in sched.get_jobs():
        print(f"  {job.id:20} next: {job.next_run_time}")
    time.sleep(40)
    sched.shutdown()

# ── 8. SUBPROCESS — run shell commands ───────────────────────────────────────
def subprocess_demo():
    # Capture output
    r = subprocess.run(["git","log","--oneline","-3"],
                       capture_output=True, text=True)
    print(r.stdout)

    # Stream live output
    with subprocess.Popen(["ping","-c","3","8.8.8.8"],
                          stdout=subprocess.PIPE, text=True) as proc:
        for line in proc.stdout: print(line, end="")

    # Timeout + error handling
    try:
        subprocess.run(["sleep","100"], timeout=2, check=True)
    except subprocess.TimeoutExpired:
        print("Process timed out — killed")
    except subprocess.CalledProcessError as e:
        print(f"Exit {e.returncode}: {e.stderr}")

# ── 9. CRON — manage crontab from Python ─────────────────────────────────────
# pip install python-crontab
from crontab import CronTab

def cron_demo():
    cron = CronTab(user=True)
    job  = cron.new(command="/usr/bin/python3 /home/user/scrape.py",
                    comment="daily_scraper")
    job.setall("0 8 * * *")       # every day at 08:00
    cron.write()
    print("Cron jobs:")
    for j in cron: print(" ", j)
    cron.remove_all(comment="daily_scraper")
    cron.write()
    print("Cleaned up.")

# ── MAIN — choose which section to run ───────────────────────────────────────
if __name__ == "__main__":
    args = make_parser().parse_args()          # section 1 demo
    if args.verbose:
        print(f"Args: folder={args.folder}, ext={args.ext}, workers={args.workers}")

    # Uncomment whichever demo you want to run:
    organise(str(args.folder))               # section 2
    watch_folder(str(args.folder))           # section 3
    save_csv(scrape_quotes())                # sections 4
    send_alert("Test","Body","to@x.com","from@gmail.com","app_pw") # section 5
    run_schedule_demo()                      # section 6
    run_apscheduler_demo()                   # section 7
    subprocess_demo()                        # section 8
    cron_demo()                              # section 9
