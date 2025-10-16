"""
Remotely draw names for a Secret Santa

Only works with gmail as-written.

Set the following env vars:
    EMAIL: host email, from which all emails will be sent
    EMAIL_APP_PASS: generated application password (not normal login password)
    PARTY: yaml file containing participants, their emails, and forbidden picks
"""
import os
import smtplib
from random import randint
from yaml import safe_dump, safe_load

# read email from env vars
EMAIL = os.getenv('EMAIL')
# read email app password from env vars (different from your "normal" password)
EMAIL_APP_PASS = os.getenv('EMAIL_APP_PASS')

class Party():
    """Class representing the collection of participants in secret santa."""

    def __init__(self):
        self.people = []
        with open(os.getenv('PARTY'), 'r', encoding="utf-8") as yam:
            data = safe_load(yam)
            for name, info in data.items():
                self.people.append(Person(name, info))

class Person():
    """Class representing a single participant in secret santa."""

    def __init__(self, name, info):
        self.name = name
        self.email = info['email']
        self.forbidden = info['forbidden']
        self.giftee = None

class Hat():
    """Class representing hat of names."""

    def __init__(self):
        with open(os.getenv('PARTY'), 'r', encoding="utf-8") as yam:
            data = safe_load(yam)
            self.names = [person for person in data]

    def draw(self, group):
        """
        Each participant in the group will draw names from the hat.
        Tries to avoid themselves and forbidden.

        Args:
            group (Party)
        """
        for participant in group.people:
            # prune hat before drawing
            pruned = []
            # remove person drawing
            try:
                self.names.remove(participant.name)
                pruned.append(participant.name)
            except ValueError:
                pass
            # remove forbidden
            for name in participant.forbidden:
                try:
                    self.names.remove(name)
                    pruned.append(name)
                except ValueError:
                    pass
            # if none left, try to reconcile
            if len(self.names) == 0:
                # take last pruned and try to make a viable swap
                giftee = pruned.pop()
                # look at party (not current person or their forbidden)
                for other in [p for p in group.people \
                    if p.name != group.name and p.name not in participant.forbidden]:
                    # see if their giftee works for current person
                    if giftee not in other.forbidden and \
                        other.giftee not in participant.forbidden and \
                        other.giftee != participant.name:
                        # swap
                        new_giftee = other.giftee
                        other.giftee = giftee
                        giftee = new_giftee
                        break
            else:
                # draw
                giftee = self.names.pop(randint(0, len(self.names)-1))
            participant.giftee = giftee
            # replace pruned
            self.names.extend(pruned)

def email(participant):
    """
    Sends email from host EMAIL to person, informing of giftee drawn.

    Only works with gmail as-written.

    Args:
        participant (Person): party participant
    """
    # build email
    subject = 'Secret Santa'
    body = (f"Hello {participant.name}!\n\n"
            f"You are the Secret Santa for {participant.giftee}!\n\n")

    # bring everything together
    email_text = (f"From: {EMAIL}\n"
                    f"To: {participant.email}\n"
                    f"Subject: {subject}\n"
                    f"{body}")

    try:
        # send email
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(EMAIL, EMAIL_APP_PASS)
        server.sendmail(EMAIL, participant.email, email_text)
        server.close()
        print('Email sent!')
    except smtplib.SMTPException as smtp_err:
        print('Something went wrong during email...')
        print(smtp_err)

if __name__ == "__main__":
    # list of participants from PARTY yaml
    party = Party()
    # a simple list of names in PARTY for the "hat"
    hat = Hat()

    # run the secret santa drawing
    hat.draw(party)

    for person in party.people:
        if not person.giftee:
            print(f"Something isn't quite right. {person.name} got {person.giftee}.")
            exit(1)

    # email participants
    for person in party.people:
        email(person)

    # build new party yaml for next time
    party_dict = {}
    for person in party.people:
        new_forbidden = person.forbidden
        # only preserve original forbidden
        if len(new_forbidden) > 1:
            new_forbidden = person.forbidden[:-1]
        # add new giftee as forbidden
        new_forbidden.append(person.giftee)
        party_dict[person.name] = {
            'email': person.email,
            'forbidden': new_forbidden,
        }
    with open("next.yaml", 'w') as next_yam:
        safe_dump(party_dict, next_yam)

