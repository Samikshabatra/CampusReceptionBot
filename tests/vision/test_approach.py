from reception.config import VisionConfig
from reception.vision.approach import ApproachDetector, Box

CFG = VisionConfig()


def run(frames: list[tuple[float, list[Box]]]) -> list[str]:
    d = ApproachDetector(CFG)
    kinds: list[str] = []
    for t, boxes in frames:
        kinds += [e.kind for e in d.update(boxes, t)]
    return kinds


def seq(n: int, fps: float, fn) -> list[tuple[float, list[Box]]]:  # type: ignore[no-untyped-def]
    return [(i / fps, fn(i / fps)) for i in range(n)]


def test_approach_triggers_once() -> None:
    frames = seq(15, 5, lambda t: [Box(0.45, 0.3, 0.08 + 0.03 * t, 0.10 + 0.04 * t)])
    assert run(frames).count("approach") == 1


def test_walk_past_does_not_trigger() -> None:
    frames = seq(15, 5, lambda t: [Box(0.05 + 0.3 * t, 0.3, 0.09, 0.12)])
    assert "approach" not in run(frames)


def test_standing_far_does_not_trigger() -> None:
    frames = seq(20, 5, lambda t: [Box(0.47, 0.3, 0.05, 0.07)])
    assert "approach" not in run(frames)


def test_lingering_near_person_greeted_once() -> None:
    frames = seq(60, 5, lambda t: [Box(0.4, 0.25, 0.16, 0.22)])
    assert run(frames).count("approach") == 1


def test_off_centre_near_person_not_greeted() -> None:
    frames = seq(20, 5, lambda t: [Box(0.85, 0.25, 0.12, 0.22)])
    assert "approach" not in run(frames)


def test_crowd_event() -> None:
    frames = seq(10, 5, lambda t: [Box(0.2, 0.3, 0.15, 0.2), Box(0.6, 0.3, 0.15, 0.2)])
    assert "crowd" in run(frames)


def test_left_event_after_absence() -> None:
    near = seq(15, 5, lambda t: [Box(0.42, 0.25, 0.16, 0.22)])
    gone = [(3.0 + i / 5, []) for i in range(15)]
    kinds = run(near + gone)
    assert kinds.index("approach") < kinds.index("left")


def test_present_flag() -> None:
    d = ApproachDetector(CFG)
    d.update([Box(0.4, 0.25, 0.16, 0.22)], 0.0)
    assert d.present
    d.update([], 5.0)
    assert not d.present


def test_face_held_still_in_front_greets() -> None:
    # Someone standing still at a normal distance (not walking closer) is greeted once.
    frames = seq(10, 5, lambda t: [Box(0.44, 0.3, 0.1, 0.13)])
    kinds = run(frames)
    assert kinds.count("approach") == 1


def test_face_held_less_than_dwell_does_not_greet() -> None:
    frames = seq(4, 5, lambda t: [Box(0.44, 0.3, 0.1, 0.13)])  # 0.6 s
    assert "approach" not in run(frames)
