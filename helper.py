from datetime import datetime, timedelta
import pytz
from os import environ

utc = pytz.utc
localtz = pytz.timezone(environ["TIMEZONE"])

def convertToDateTime(x: str) -> datetime:
    dt = datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ")
    return dt.replace(tzinfo=utc)

def format_date(dt: datetime) -> str:
    return dt.astimezone(localtz).strftime("%Y-%m-%d %H:%M:%S")

def trim_and_format(x: str) -> str:
    if len(x) > 200:
        x = x[:200] + "..."
    return ">" + x.strip().replace("\n", "\n> ")

def get_n_day_prior(n: int) -> datetime:
    return datetime.now(utc) - timedelta(days=n)
