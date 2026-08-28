import redis.asyncio as redis

SESSION_KEY_PREFIX = "session:"


class SessionStore:
    """Simpan session aktif per user di Redis.

    Satu key per user (`session:{user_id}`) = single session: login baru
    menimpa value lama, sehingga token session sebelumnya tidak valid lagi.
    TTL = refresh token expiry (session mati walau user tidak logout).
    """

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    @staticmethod
    def _key(user_id: int) -> str:
        return f"{SESSION_KEY_PREFIX}{user_id}"

    async def create(self, user_id: int, session_id: str, ttl_seconds: int) -> None:
        await self._redis.set(
            self._key(user_id),
            session_id,
            ex=ttl_seconds,
        )

    async def validate(self, user_id: int, session_id: str) -> bool:
        stored = await self._redis.get(self._key(user_id))

        if stored is None:
            return False

        return stored.decode("utf-8") == session_id

    async def delete(self, user_id: int) -> None:
        await self._redis.delete(self._key(user_id))
