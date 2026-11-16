from reception.types import Card, Response


def test_response_defaults() -> None:
    r = Response(speech="hi", card=Card(kind="text", data={}), intent="greeting", confidence=1.0)
    assert r.links == [] and r.verified is True and r.handover_reason is None
