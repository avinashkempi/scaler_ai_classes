"""
test_bill_splitter.py - tests for bill_splitter.py (run with: pytest -q)

Author: Shivank Agrawal
Project: Mini Cursor sample workspace - Future with Shivank
"""

import pytest

from bill_splitter import split_bill


def test_even_split_with_tip():
    assert split_bill(1000, 4, tip_percent=10) == 275.0


def test_no_tip():
    assert split_bill(900, 3, tip_percent=0) == 300.0


def test_rounding():
    assert split_bill(100, 3, tip_percent=0) == 33.33


def test_zero_people_is_an_error():
    with pytest.raises(ValueError):
        split_bill(100, 0)
