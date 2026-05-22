import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('DB_URL')
print(URL)