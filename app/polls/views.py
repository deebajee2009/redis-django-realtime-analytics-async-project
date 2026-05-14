"""
Polls App views.
"""
from typing import List

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from ninja import Router, Header

from .models import Poll
from .schema import (
    PollOutListSchema,
    CreatePollSchema,
    PollOutSchema,
    ErrorSchema,
    VoteSchema,
)
from polls.services.redis_poll_services import (
    record_vote,
    try_register_vote,
    is_rate_limited,
)
from polls.services.ip_services import get_client_ip
from polls.services.cookie_services import (
    set_vote_cookie,
    has_cookie_voted,
)
from polls.services.redis_poll_reporting import (
    get_poll_vote_counts,
    get_cached_poll_results,
    cache_poll_results,
)


router = Router()

@router.get("/polls", response=List[PollOutListSchema])
async def poll_list(request):
    """
    Docstring for poll_list

    :param request: Description
    """
    polls = await sync_to_async(list)(Poll.objects.all())
    return polls

@router.post("/polls/add", response={201: PollOutSchema, 400: ErrorSchema})
async def create_poll(request, data: CreatePollSchema):
    """
    Docstring for create_poll

    :param request: Description
    :param data: Description
    :type data: CreatePollSchema
    """
    if not data.text or len(data.text) < 2:
        return 400, {"error": "Atleast two poll options are required."}

    # Save poll to db
    # poll = Poll(question=data.question, text=data.text)
    # await poll.asave()

    # Nicer version
    poll = await Poll.objects.acreate(question=data.question, text=data.text)

    return 201, poll

@router.post("/polls/{poll_id}/vote", response={200: dict, 400: ErrorSchema})
async def vote(request, poll_id: int, data: VoteSchema, x_user_id: str = Header(None)):
    """
    Docstring for vote

    :param request: Description
    :param poll_id: Description
    :type poll_id: int
    :param data: Description
    :type data: VoteSchema
    """
    option_id = data.option

    # 1. Validate poll & option
    try:
        poll = await Poll.objects.aget(pk=poll_id)
    except Poll.DoesNotExist:
        return 404, {"error": "Poll not found."}

    # 1.1 Enforce status and expiry
    if not poll.is_active:
        return 400, {"error": "This poll is not active."}

    if poll.expires_at and poll.is_expired():
        return 400, {"error": "This poll has expired."}

    if option_id not in poll.text:
        return 400, {"error": "Invalid option ID."}

    # 2. Get identity
    ip = get_client_ip(request)
    user_id = request.headers.get("X-USER-ID")

    # 2.1 Rate limit check (before anything else)
    if await is_rate_limited(ip):
        return 400, {"error": "You're voting too quickly. Please wait a few seconds."}

    if user_id:
        success = await try_register_vote(poll_id, user_id, "voted_users")
        if not success:
            return 400, {"error": "User has already voted."}

    # Previous version
    # if user_id:
    #     if await has_user_voted(poll_id, user_id):
    #         return 400, {"error": "User has already voted"}
    #     await register_user_vote(poll_id, user_id)

    # 3. Check by ip or cookie the user has voted before
    ip_already_voted = not await try_register_vote(poll_id, ip, "voted_ips")

    if ip_already_voted or has_cookie_voted(request, poll_id):
        return 400, {"error": "This IP/Browser has already voted."}

    # 4. Register user's vote
    await record_vote(poll_id, option_id, user_id or "anonymous", ip)

    # 5. Return success + set cookie
    response = JsonResponse({"message": f"Vote for option {option_id} counted"})
    set_vote_cookie(response, request, poll_id)

    return response

@router.get("/polls/{poll_id}/results", response={200: dict, 400: ErrorSchema, 404: ErrorSchema})
async def poll_results(request, poll_id: int):
    """
    Docstring for poll_results

    :param request: Description
    :param poll_id: Description
    :type poll_id: int
    """
    # Try cache first
    cached = await get_cached_poll_results(poll_id)
    if cached:
        return cached

    # 1. Get poll metadata from database
    try:
        poll = await Poll.objects.aget(pk=poll_id)
    except Poll.DoesNotExist:
        return 404, {"error": "Poll not found."}

    # 2. Get poll counts
    results = await get_poll_vote_counts(poll_id)

    # 3. Check if some key not votes set value 0
    for option_id in poll.text.keys():
        if option_id not in results:
            results[option_id] = 0

    # 4. Sum of all votes
    total_votes = sum(results.values())

    # 5. Prepare outcome dict
    response = {
        "poll_id": poll.id,
        "question": poll.question,
        "options": [{"id": k, "text": v} for k, v in poll.text.items()],
        "results": results,
        "total_votes": total_votes,
    }

    await cache_poll_results(poll_id, response) # Cache it for next time
    return response