<p align="center">
  <a href="github.com/belectron13/rubox">
    <img src="https://raw.githubusercontent.com/BELECTRON13/rubox/refs/heads/main/HoshaAI-1%20(1).png" width=260 height=210 alt="Rubox" />
  </a>
</p>

---

## 🔧 Rubox
> **A powerful library designed for building bots on the Rubika platform.**

---

### 🛠 Simple Example
```python
from rubox import Client
from rubox.filters import commands
import asyncio

TOKEN = "BOT-TOKEN"

async def main():
	async with Client(TOKEN) as app:
		@app.on_message(commands('start', 'help'))
		async def start_handler(message):
			await message.reply('Hello from Rubox!')
			
		await app.run()
		
asyncio.run(main())		
```

### 👾 Minimal Example
```python
from rubox import Client
import asyncio

TOKEN = "BOT-TOKEN"

async def main():
	async with Client(TOKEN) as app:
		await app.send_message('chat_id', 'Hello from **Rubox**!')
		
asyncio.run(main())
```

### 🌐 Webhook Setup
```python

```

###  📦 Installation
```bash
pip install -U rubox
```








