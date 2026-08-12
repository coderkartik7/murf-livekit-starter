import asyncio
import services
from agent import make_outbound_call

from dotenv import load_dotenv
load_dotenv(".env.local")

low = services.get_low_stock_products(threshold=5)
item = low[0]["name"] if low else "an item"
asyncio.run(make_outbound_call("coderkartik", "restock-alert-room", item))