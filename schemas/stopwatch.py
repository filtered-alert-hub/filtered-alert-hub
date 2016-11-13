import time


class Stopwatch(object):
    """A stopwatch utility for timing execution that can be used as a regular
    object or as a context manager.

    NOTE: This should not be used an accurate benchmark of Python code, but a
    way to check how much time has elapsed between actions. And this does not
    account for changes or blips in the system clock.

    Instance attributes:
    start_time -- timestamp when the timer started
    stop_time -- timestamp when the timer stopped

    As a regular object:

    >>> stopwatch = Stopwatch()
    >>> stopwatch.start()
    >>> time.sleep(1)
    >>> 1 <= stopwatch.time_elapsed <= 2
    True
    >>> time.sleep(1)
    >>> stopwatch.stop()
    >>> 2 <= stopwatch.total_run_time
    True

    As a context manager:

    >>> with Stopwatch() as stopwatch:
    ...     time.sleep(1)
    ...     print repr(1 <= stopwatch.time_elapsed <= 2)
    ...     time.sleep(1)
    True
    >>> 2 <= stopwatch.total_run_time
    True
    """

    def __init__(self):
        """Initialize a new `Stopwatch`, but do not start timing."""
        self.start_time = None
        self.stop_time = None

    def start(self):
        """Start timing."""
        self.start_time = time.time()

    def stop(self):
        """Stop timing."""
        self.stop_time = time.time()

    @property
    def time_elapsed(self):
        """Return the number of seconds that have elapsed since this
        `Stopwatch` started timing.

        This is used for checking how much time has elapsed while the timer is
        still running.
        """
        assert not self.stop_time, \
            "Can't check `time_elapsed` on an ended `Stopwatch`."
        return time.time() - self.start_time

    @property
    def total_run_time(self):
        """Return the number of seconds that elapsed from when this `Stopwatch`
        started to when it ended.
        """
        return self.stop_time - self.start_time

    def __enter__(self):
        """Start timing and return this `Stopwatch` instance."""
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        """Stop timing.

        If there was an exception inside the `with` block, re-raise it.

        >>> with Stopwatch() as stopwatch:
        ...     raise Exception
        Traceback (most recent call last):
            ...
        Exception
        """
        self.stop()
        if type:
            raise type, value, traceback
