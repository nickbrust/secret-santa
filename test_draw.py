"""Checks for the drawing. Run with: python3 -m unittest test_draw"""
import unittest
from draw import Hat, Party

class TestDraw(unittest.TestCase):
    """Drawing gives a valid result, or raises when none exists."""

    def test_valid_drawing(self):
        for _ in range(100):
            party = Party('sample-party.yaml')
            Hat(party).draw(party)
            names = sorted(p.name for p in party.people)
            self.assertEqual(sorted(p.giftee for p in party.people), names)
            for person in party.people:
                self.assertTrue(person.can_draw(person.giftee), person.name)

    def test_impossible_drawing_raises(self):
        party = Party('sample-party.yaml')
        for person in party.people:
            person.forbidden = [p.name for p in party.people]
        with self.assertRaises(ValueError):
            Hat(party).draw(party)

if __name__ == "__main__":
    unittest.main()
