from datetime import date, time

from reception.speech_format import speak_date, speak_inr, speak_money, speak_phone, speak_time


def test_speak_inr() -> None:
    assert [speak_inr(x) for x in (242000, 99000, 1250000, 5000, 200000, 90000)] == [
        "2 lakh 42 thousand rupees",
        "99 thousand rupees",
        "12 lakh 50 thousand rupees",
        "5 thousand rupees",
        "2 lakh rupees",
        "90 thousand rupees",
    ]


def test_speak_money_foreign() -> None:
    assert speak_money(2375, "USD") == "2,375 US dollars"
    assert speak_money(2500, "EUR") == "2,500 euros"
    assert speak_money(242000, "INR") == "2 lakh 42 thousand rupees"


def test_speak_phone() -> None:
    assert speak_phone("+91 80 4012 9100") == "plus 9 1, 8 0, 4 0 1 2, 9 1 0 0"


def test_speak_time_and_date() -> None:
    assert speak_time(time(10)) == "10 am"
    assert speak_time(time(13)) == "1 pm"
    assert speak_time(time(8, 30)) == "8:30 am"
    assert speak_time(time(12)) == "12 noon"
    assert speak_date(date(2026, 11, 21)) == "21 November"
