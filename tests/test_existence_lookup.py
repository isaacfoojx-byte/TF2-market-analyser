import unittest

from scraper.existence_lookup import parse_existence_count, unusual_item_url


SAMPLE_HTML = """
<table>
  <tbody>
    <tr>
      <td><a>Burning Flames</a></td><td>63 keys</td><td>~12</td>
    </tr>
    <tr>
      <td><a>Sunbeams</a></td><td>59 keys</td><td>~9</td>
    </tr>
  </tbody>
</table>
"""


class ExistenceLookupTests(unittest.TestCase):
    def test_parses_the_count_for_the_requested_effect(self):
        self.assertEqual(parse_existence_count(SAMPLE_HTML, "Burning Flames"), 12)
        self.assertEqual(parse_existence_count(SAMPLE_HTML, "Sunbeams"), 9)

    def test_returns_none_when_the_effect_is_not_present(self):
        self.assertIsNone(parse_existence_count(SAMPLE_HTML, "Aces High"))

    def test_quotes_item_names_in_the_source_url(self):
        self.assertEqual(
            unusual_item_url("Team Captain"),
            "https://backpack.tf/unusual/Team%20Captain?view=list",
        )


if __name__ == "__main__":
    unittest.main()
