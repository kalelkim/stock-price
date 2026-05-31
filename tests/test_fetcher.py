import pandas as pd
import pytest

from stock_price.fetcher import FetchError, fetch_latest


def _df():
    return pd.DataFrame({"Close": [1.0, 2.0]},
                        index=pd.date_range("2026-05-28", periods=2))


class Reader:
    """fail_times번 실패(빈 DataFrame 또는 예외) 후 df 반환하는 가짜 reader."""

    def __init__(self, fail_times, df=None, raises=False):
        self.calls = 0
        self.fail_times = fail_times
        self.df = df
        self.raises = raises

    def __call__(self, symbol):
        self.calls += 1
        if self.calls <= self.fail_times:
            if self.raises:
                raise RuntimeError("boom")
            return pd.DataFrame()  # 빈 결과
        return self.df


def test_returns_on_first_success():
    df = _df()
    reader = Reader(fail_times=0, df=df)
    sleeps = []
    out = fetch_latest("AAA", reader, sleep=lambda s: sleeps.append(s))
    assert out is df
    assert reader.calls == 1
    assert sleeps == []


def test_retries_then_succeeds():
    df = _df()
    reader = Reader(fail_times=2, df=df, raises=True)
    sleeps = []
    out = fetch_latest("AAA", reader, retries=3, sleep=lambda s: sleeps.append(s))
    assert out is df
    assert reader.calls == 3
    assert len(sleeps) == 2


def test_empty_always_raises_fetcherror():
    reader = Reader(fail_times=99)  # 항상 빈 결과
    sleeps = []
    with pytest.raises(FetchError):
        fetch_latest("AAA", reader, retries=3, sleep=lambda s: sleeps.append(s))
    assert reader.calls == 3
    assert len(sleeps) == 2


def test_exception_always_raises_fetcherror_with_symbol():
    reader = Reader(fail_times=99, raises=True)
    with pytest.raises(FetchError) as exc:
        fetch_latest("ZZZ", reader, retries=2, sleep=lambda s: None)
    assert "ZZZ" in str(exc.value)
