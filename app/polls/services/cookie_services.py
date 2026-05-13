"""
Module for handling cookie related functions.
"""
VOTE_COOKIE_NAME = "poll_voted"
VOTE_EXPIRY = 30 * 24 * 60 * 60 # 30 days

def has_cookie_voted(request, poll_id: int) -> bool:
    """
    Check cookie via poll_id

    :param request: Description
    :param poll_id: Description
    :type poll_id: int
    :return: Description
    :rtype: bool
    """
    voted_polls = request.COOKIES.get(VOTE_COOKIE_NAME, "")
    return str(poll_id) in voted_polls.split(",")

def set_vote_cookie(response, request, poll_id: int):
    existing = request.COOKIES.get(VOTE_COOKIE_NAME, "")
    voted_polls = set(existing.split(",")) if existing else set()
    voted_polls.add(str(poll_id))
    response.set_cookie(VOTE_COOKIE_NAME, ",".join(voted_polls), max_age=VOTE_EXPIRY)