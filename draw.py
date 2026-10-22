"""
Remotely draw names for a Secret Santa

Only works with gmail as-written.

Set the following env vars:
    EMAIL: host email, from which all emails will be sent
    EMAIL_APP_PASS: generated application password (not normal login password)
    PARTY: yaml file containing participants, their emails, and forbidden picks

Each participant in the PARTY yaml has:
    email: where to send their giftee
    forbidden: names they should never draw (e.g. their partner)
    last_year: (optional) who they drew last time; also avoided this time
"""
import os
import random
import smtplib
import sys
from email.message import EmailMessage
from yaml import safe_dump, safe_load

# read email from env vars
EMAIL = os.getenv('EMAIL')
# read email app password from env vars (different from your "normal" password)
EMAIL_APP_PASS = os.getenv('EMAIL_APP_PASS')

class Party():
    """Class representing the collection of participants in secret santa."""

    def __init__(self, path):
        self.people = []
        with open(path, 'r', encoding="utf-8") as yam:
            data = safe_load(yam)
            for name, info in data.items():
                self.people.append(Person(name, info))

class Person():
    """Class representing a single participant in secret santa."""

    def __init__(self, name, info):
        self.name = name
        self.email = info['email']
        # permanent exclusions, carried over to next year as-is
        self.forbidden = list(info.get('forbidden') or [])
        # who they drew last time, only avoided for this drawing
        self.last_year = info.get('last_year')
        self.giftee = None

    def can_draw(self, name):
        """Whether this person is allowed to draw the given name."""
        return name not in (self.name, self.last_year, *self.forbidden)

class Hat():
    """Class representing hat of names."""

    def __init__(self, group):
        self.names = [person.name for person in group.people]

    def draw(self, group):
        """
        Each participant in the group will draw a name from the hat,
        never themselves, their forbidden, or last year's giftee.

        Searches every arrangement (in random order) so a valid drawing
        is always found if one exists.

        Args:
            group (Party)

        Raises:
            ValueError: if no valid drawing exists
        """
        # most constrained people draw first so dead ends show up early
        drawers = sorted(group.people,
                         key=lambda p: sum(p.can_draw(n) for n in self.names))
        if not self._assign(drawers, set(self.names)):
            raise ValueError("No valid drawing exists with these forbidden picks.")

    def _assign(self, drawers, remaining):
        """Recursively give each drawer a name from remaining, backtracking on dead ends."""
        if not drawers:
            return True
        participant, rest = drawers[0], drawers[1:]
        options = [name for name in remaining if participant.can_draw(name)]
        random.shuffle(options)
        for name in options:
            participant.giftee = name
            if self._assign(rest, remaining - {name}):
                return True
        participant.giftee = None
        return False

def build_email(participant):
    """
    Builds the email from host EMAIL to person, informing of giftee drawn.

    Args:
        participant (Person): party participant

    Returns:
        EmailMessage
    """
    msg = EmailMessage()
    msg['From'] = EMAIL
    msg['To'] = participant.email
    msg['Subject'] = 'Secret Santa'
    msg.set_content(f"Hello {participant.name}!\n\n"
                    f"You are the Secret Santa for {participant.giftee}!\n")
    return msg

def email_all(group):
    """
    Sends each participant their giftee over a single gmail connection.

    Only works with gmail as-written.

    Args:
        group (Party)
    """
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL, EMAIL_APP_PASS)
            for participant in group.people:
                server.send_message(build_email(participant))
                print(f'Email sent to {participant.name}!')
    except smtplib.SMTPException as smtp_err:
        print('Something went wrong during email...')
        print(smtp_err)
        sys.exit(1)

if __name__ == "__main__":
    # list of participants from PARTY yaml
    party = Party(os.getenv('PARTY'))
    # a simple list of names in PARTY for the "hat"
    hat = Hat(party)

    # run the secret santa drawing
    try:
        hat.draw(party)
    except ValueError as err:
        print(err)
        sys.exit(1)

    # email participants
    email_all(party)

    # build new party yaml for next time
    party_dict = {}
    for person in party.people:
        party_dict[person.name] = {
            'email': person.email,
            'forbidden': person.forbidden,
            'last_year': person.giftee,
        }
    with open("next.yaml", 'w', encoding="utf-8") as next_yam:
        safe_dump(party_dict, next_yam, sort_keys=False)
