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
from copy import deepcopy
from random import randint
from yaml import safe_load

# read email from env vars
EMAIL = os.getenv('EMAIL')
# read email app password from env vars (different from your "normal" password)
EMAIL_APP_PASS = os.getenv('EMAIL_APP_PASS')

class Party():

    def __init__(self):
        self.people = []
        with open(os.getenv('PARTY'), 'r') as yam:
            party = safe_load(yam)
            for name, info in party.items():
                self.people.append(Person(name, info))

class Person():

    def __init__(self, name, info):
        self.name = name
        self.email = info['email']
        self.forbidden = info['forbidden']
        self.giftee = None

class Hat():

    def __init__(self):
        with open(os.getenv('PARTY'), 'r') as yam:
            party = safe_load(yam)
            self.names = [person for person in party]

    def draw(self, party):
        for person in party.people:
            # prune hat before drawing
            pruned = []
            # remove person drawing
            try:
                self.names.remove(person.name)
                pruned.append(person.name)
            except ValueError as val_err:
                pass
            # remove forbidden
            for name in person.forbidden:
                try:
                    self.names.remove(name)
                    pruned.append(name)
                except ValueError as val_err:
                    pass
            # if none left, try to reconcile
            if len(self.names) == 0:
                # take last pruned and try to make a viable swap
                giftee = pruned.pop()
                # look at party (not current person or their forbidden)
                for other in [p for p in party.people if p.name != person.name and p.name not in person.forbidden]:
                    # see if their giftee works for current person
                    if giftee not in other.forbidden and (other.giftee not in person.forbidden and other.giftee != person.name):
                        # swap
                        new_giftee = other.giftee
                        other.giftee = giftee
                        giftee = new_giftee
                        break
            else:
                # draw
                giftee = self.names.pop(randint(0, len(self.names)-1))
            person.giftee = giftee
            # replace pruned
            self.names.extend(pruned)

def email(person):
    """
    Sends email from host EMAIL to person, informing of giftee drawn.

    Only works with gmail as-written.

    Args:
        person (Person): party participant
    """
    # build email
    subject = 'Secret Santa'
    body = (f"Hello {person.name}!\n\n"
            f"You are the Secret Santa for {person.giftee}!\n\n")

    # bring everything together
    email_text = (f"From: {EMAIL}\n"
                    f"To: {person.email}\n"
                    f"Subject: {subject}\n"
                    f"{body}")

    try:
        # send email
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(EMAIL, EMAIL_APP_PASS)
        server.sendmail(EMAIL, person.email, email_text)
        server.close()
        print('Email sent!')
    except:
        print('Something went wrong...')

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
