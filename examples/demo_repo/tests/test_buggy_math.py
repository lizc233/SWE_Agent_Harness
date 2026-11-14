import unittest

from buggy_math import average, percentage


class MathTests(unittest.TestCase):
    def test_average(self) -> None:
        self.assertEqual(average([2, 4]), 3)

    def test_percentage_returns_zero_when_total_is_zero(self) -> None:
        self.assertEqual(percentage(5, 0), 0.0)


if __name__ == "__main__":
    unittest.main()

