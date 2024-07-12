from application import app
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from application import db

def clear_db():
    db.meals.delete_many({})
    print("Database cleared at the end of the day")

scheduler = BackgroundScheduler()
scheduler.add_job(func=clear_db, trigger='cron', hour=23, minute=59)  # Adjust the time as needed
scheduler.start()

if __name__ == "__main__":
  try:
    app.run(debug=True)
  except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()