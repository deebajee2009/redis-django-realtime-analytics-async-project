"""
Polls App views.
"""
from typing import List

from asgiref.sync import sync_to_async
from ninja import Router

from .models import Poll
from .schema import (
    PollOutListSchema,
    CreatePollSchema,
    PollOutSchema,
    ErrorSchema,
    VoteSchema,
)
from polls.services.redis_poll_services import (
    increment_vote,
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
async def vote(request, poll_id: int, data: VoteSchema):
    """
    Docstring for vote

    :param request: Description
    :param poll_id: Description
    :type poll_id: int
    :param data: Description
    :type data: VoteSchema
    """
    option_id = data.option

    try:
        poll = await Poll.objects.aget(pk=poll_id)
    except Poll.DoesNotExist:
        return 404, {"error": "Poll not found."}

    if option_id not in poll.text:
        return 400, {"error": "Invalid option ID."}

    await increment_vote(poll_id, option_id)

    return {"message": f"Vote for option {option_id} counted"}