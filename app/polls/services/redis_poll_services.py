"""
Redis module for poll management.
"""
import json

from django.conf import settings

from redis_poll_reporting import delete_cached_poll_results


r = settings.REDIS_CLIENT

RATE_LIMIT_SECONDS = 5

async def is_rate_limited(ip: str) -> bool:
    """
    Check if the user has voted in previous seconds.

    :param ip: Description
    :type ip: str
    :return: Description
    :rtype: bool
    """
    key = f"rate_limit:{ip}"
    added = await r.set(key, 1, ex=RATE_LIMIT_SECONDS, nx=True)
    return added is None  # If key already exists, rate limited.

def get_poll_key(poll_id: int, suffix: str) -> str:
    """
    Docstring for get_poll_key
    """
    return f"poll:{poll_id}:{suffix}"

# In continue we combine these two functions as single one
# async def increment_vote(poll_id: int, option_id: str) -> None:
#     """
#     Increment the vote counter for an option.
#     """
#     key = get_poll_key(poll_id, "votes")
#     await r.hincrby(key, option_id, 1)

# async def track_recent_vote(poll_id: int, user_id: str, ip: str, option_id: str) -> None:
#     """
#     Docstring for track_recent_vote

#     :param poll_id: Description
#     :type poll_id: int
#     :param user_id: Description
#     :type user_id: str
#     :param ip: Description
#     :type ip: str
#     :param option_id: Description
#     :type option_id: str
#     """
#     key = get_poll_key(poll_id, "recent_votes")

#     vote_data = {
#         "user_id": user_id,
#         "ip": ip,
#         "option_id": option_id,
#     }
#     await r.lpush(key, json.dumps(vote_data))
#     await r.ltrim(key, 0, 99)  # Keep only last 100 entries

async def record_vote(poll_id: int, option_id: str, voter_id: str, ip: str):
    """
    Register vote and the track the last 100 votes

    :param poll_id: Description
    :type poll_id: int
    :param option_id: Description
    :type option_id: str
    :param voter_id: Description
    :type voter_id: str
    :param ip: Description
    :type ip: str
    """
    vote_key = get_poll_key(poll_id, "votes")
    recent_key = get_poll_key(poll_id, "recent_votes")

    vote_data = {
        "user_id": voter_id,
        "ip": ip,
        "option_id": option_id
    }

    async with r.pipeline(transaction=True) as pipe:
        pipe.hincrby(vote_key, option_id, 1)
        pipe.lpush(recent_key, json.dumps(vote_data))
        pipe.ltrim(recent_key, 0, 99)
        await pipe.execute()

    # Invalidate the cached results
    await delete_cached_poll_results(poll_id)

async def try_register_vote(poll_id: int, voter_id: str, suffix: str) -> bool:
    """
    Attempts to register a user vote.
    Returns True if successful, False if user has already voted.

    :param poll_id: Description
    :type poll_id: int
    :param user_id: Description
    :type user_id: str
    :return: Description
    :rtype: bool
    """
    key = get_poll_key(poll_id, suffix)
    added = await r.sadd(key, voter_id)
    return added == 1  # 1 = added, 0 = already existed


# async def register_user_vote(poll_id: int, user_id: str) -> None:
#     """
#     register a user as having voted.

#     :param poll_id: Description
#     :type poll_id: int
#     :param user_id: Description
#     :type user_id: str
#     """
#     key = get_poll_key(poll_id, "voted_users")
#     await r.sadd(key, user_id)

# async def has_user_voted(poll_id: int, user_id:str) -> bool:
#     """
#     Check if user has already voted in the poll.

#     :param poll_id: Description
#     :type poll_id: int
#     :param user_id: Description
#     :type user_id: str
#     :return: Description
#     :rtype: bool
#     """
#     key = get_poll_key(poll_id, "voted_users")
#     return await r.sismember(key, user_id)


async def get_recent_votes(poll_id: int) -> list:
    """
    Docstring for get_recent_votes

    :param poll_id: Description
    :type poll_id: int
    :return: Description
    :rtype: list
    """
    key = get_poll_key(poll_id, "recent_votes")
    votes = await r.lrange(key, 0, 99)
    return [json.loads(v) for v in votes]