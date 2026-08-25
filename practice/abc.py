from abc import ABC,abstractmethod
import asyncio

class LLMClient(ABC):
    
    @abstractmethod
    async def chat(self, message: str) -> str:
        pass


class OpenAIClient(LLMClient):

    async def chat(self, message):
        return f"OpenAIClient: {message}"
    
class AnthropicClient(LLMClient):

    async def chat(self, message):
        return f"AnthropicClient: {message}"

class FakeLLM(LLMClient):

    async def chat(self, message):
        return "Fake"
    
class MyClient(LLMClient):
    pass


class ChatService():

    async def ask(
            self,
            client: LLMClient,
            message: str
    ):
        return await client.chat(message)

async def main():

    service = ChatService()

    print(await service.ask(OpenAIClient(), "hello"))
    print(await service.ask(AnthropicClient(), "hello"))

    print(await service.ask(FakeLLM(), "fake"))

    print(await service.ask(MyClient(), "MyClient"))


if __name__ == "__main__":
    asyncio.run(main())