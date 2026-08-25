import asyncio

class OpenAIClient:
    async def chat(self, message: str) -> str:
        return f"OpenAI: {message}"
    

class AnthropicClient:
    async def chat(self, message: str) -> str:
        return f"Anthropic: {message}"
    

class ChatService:
    async def ask(self, client, message: str):
        return await client.chat(message)
    

class MyAwesomeClient:
    async def chat(self, message: str):
        return f"My Model: {message}"
    
class DatabaseClient:
    
    async def save(self):
        print("save")


async def main():
    service = ChatService()
    print(await service.ask(MyAwesomeClient(), "hello"))
    print(await service.ask(DatabaseClient(), "Hallo"))


if __name__ == "__main__":
    asyncio.run(main())