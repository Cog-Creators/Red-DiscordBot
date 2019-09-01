from collections import Counter as BaseCounter


class Counter(BaseCounter):
    def increment(self, key: str, val: int) -> int:
        """Function to increase the value of a counter.

        Parameters
        ----------
        key : str
            The counter to increase.
        val : int
            The value to increase by.

        Returns
        -------
        int
            The counter value.
        """
        self[key] += val
        return self[key]

    def decrement(self, key: str, val: int) -> int:
        """Function to decrease the value of a counter.

        Parameters
        ----------
        key : str
            The counter to decrease.
        val : int
            The value to decrease by.

        Returns
        -------
        int
            The counter value.
        """
        self[key] -= val
        return self[key]

    def set(self, key: str, val: int) -> int:
        """Function to set the value of a counter.

        Parameters
        ----------
        key : str
            The counter to set.
        val : int
            The value to set to.

        Returns
        -------
        int
            The counter value.
        """
        self[key] = val
        return val

    def get(self, key: str) -> int:
        """Function to get the value of a counter.

        Parameters
        ----------
        key : str
            The counter to get.

        Returns
        -------
        int
            The counter value.
            If counter does not exist returns 0.
        """
        return self[key]

    incr = increment
    decr = decrement
