import uuid
from datetime import timedelta

from redis.asyncio import Redis

MAILS_PER_ACCOUNT = 3
MAIL_LIMIT_WINDOW = timedelta(hours=1)


async def allow_mail(redis: Redis, account_id: uuid.UUID) -> bool:
    key = f"emails:{account_id}"
    async with redis.pipeline() as pipeline:
        count, _ = (
            await pipeline.incr(key).expire(key, MAIL_LIMIT_WINDOW, nx=True).execute()
        )
    return count <= MAILS_PER_ACCOUNT
