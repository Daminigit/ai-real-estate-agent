from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq()
models = client.models.list()
print([m.id for m in models.data])
