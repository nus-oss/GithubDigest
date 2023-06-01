from datetime import datetime, timedelta

convertToDateTime = lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ")

format_date = lambda x: x.strftime("%Y-%m-%d %H:%M:%S")

def trim_and_format(x: str) -> str:
    if len(x) > 200:
        x = x[:200] + "..."
    return ">" + x.strip().replace("\n", "\n> ")

def get_n_day_prior(n: int) -> datetime:
    return datetime.now() - timedelta(days=n)