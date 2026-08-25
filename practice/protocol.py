from typing import Protocol
import asyncio

class LLMClient(Protocol):

    async def chat(self, message: str) -> str:
        pass

class OpenAIClient:

    async def chat(self, message: str) -> str:
        return f"OpenAIClient: {message}"
    
class AnthropicClient:

    async def chat(self, message: str) -> str:
        return f"AnthropicClient: {message}"
    
class ChatService:

    async def ask(
            self,
            client: LLMClient,
            message: str
    ) -> str:
        return await client.chat(message)
    



async def main():
    service = ChatService()

    print(await service.ask(OpenAIClient(), "Hello"))
    print(await service.ask(AnthropicClient(), "Hello"))


if __name__ == "__main__":
    asyncio.run(main())