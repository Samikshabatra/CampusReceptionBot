# User study kit (task completion + SUS)

Run with at least 10 participants (students, staff, visitors). Get verbal consent; do not record faces.
If you record voices for the WER set, get written consent and store clips only in `data/eval/asr/`.

## Before each session
1. Start the kiosk: `uv run python scripts/run_kiosk.py` and open http://127.0.0.1:8765 in Chrome (full screen, allow camera and microphone).
2. Click **Start over**. Stand the participant about 2 m away, out of the camera view.

## Tasks (read one at a time; the participant may speak, type or tap)
1. Walk up to the kiosk and find out where the xerox shop is.
2. Find out whether that shop is open right now.
3. Find the fee for the MCA programme, then for an NRI student.
4. Find out when the open day is.
5. Find out how to contact the admissions office.
6. Ask for Room 806. *(Expected: the kiosk says it cannot find it and points to reception.)*
7. Find the nearest washroom.
8. Find out whether the library is open on Sunday.
9. Ask where a professor of your choice sits.
10. End the conversation.

Record for each task: completed (yes/no), number of attempts, time taken, and anything that confused them.

## Questionnaire (1 = strongly disagree … 5 = strongly agree)
1. I think that I would like to use this kiosk frequently.
2. I found the kiosk unnecessarily complex.
3. I thought the kiosk was easy to use.
4. I think that I would need help from a person to be able to use this kiosk.
5. I found the various functions of the kiosk well integrated.
6. I thought there was too much inconsistency in this kiosk.
7. I would imagine that most people would learn to use this kiosk very quickly.
8. I found the kiosk very cumbersome to use.
9. I felt very confident using the kiosk.
10. I needed to learn a lot of things before I could get going with this kiosk.

Plus: **Overall, how satisfied were you? (1–5)**

Enter answers in `eval/datasets/sus_responses.csv` (columns `q1`…`q10`, `satisfaction`, `tasks_completed`) and run
`uv run python scripts/evaluate.py --only ux`.

## Recording the speech set (WER)
Record each participant reading 15 visitor questions in the lobby (some quiet, some with background noise), 16 kHz mono WAV,
into `data/eval/asr/`, and list them in `data/eval/asr/transcripts.csv` as `file,text`. The evaluation uses these instead of the synthetic clips when present.

## Recording the camera set (visitor detection)
Record short clips (5–10 s) in the lobby: someone approaching, walking past, standing far away, two people together, empty lobby.
Label each clip in `data/eval/vision/labels.csv` as `file,should_greet` (yes/no). The synthetic check runs until these exist.
