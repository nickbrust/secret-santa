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
from dotenv import load_dotenv
from copy import deepcopy
from random import randint
from yaml import safe_load

# read email from env vars
load_dotenv()
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

    def draw(self, person, drawn=None):
        """
        Person draws names from the hat until a valid name is drawn.

        Drawing oneself or a name from one's forbidden list is invalid.

        Args:
            person (Person): person drawing the name
            drawn (list): forbidden names already drawn by person

        Returns:
            str||bool: name drawn or False if valid name is impossible to draw
        """
        # use deepcopy to avoid modifying hat in-place
        backup_hat = deepcopy(self.names)
        # if last name in the hat is the person drawing or in their forbidden
        if len(self.names) == 1 and (self.names[0] == person.name or self.names[0] in person.forbidden):
            # return False to signal a full redraw
            return False
        # create empty drawn list on inital call of draw()
        if drawn is None:
            drawn = []
        # draw a random name from the hat
        drawn.append(self.names.pop(randint(0, len(self.names)-1)))
        # if drawn self or forbidden
        if drawn[-1] == person.name or drawn[-1] in person.forbidden:
            print("draw again...")
            # try again, keep track of previously drawn names
            self.names = backup_hat
            return self.draw(person, drawn)
        # otherwise return the last (valid) drawn name
        return drawn[-1]

    def draw_names(self, party):
        """
        Cycles through party, having each person draw a name from the hat.

        Performs redraws until a valid conclusion is reached.
        Modifies party in-place by updating each participant's 'giftee'.

        Args:
            party (Party): list of participants (dict)
        """
        # use deepcopy to avoid modifying hat and party in-place (used for redraws)
        backup_hat = deepcopy(self.names)
        backup_party = deepcopy(party)
        # cycle through party
        for person in party.people:
            # draw a name to be giftee
            giftee = self.draw(person)
            # False signals a full redraw
            if not giftee:
                print("redraw...")
                self.names = backup_hat
                return self.draw_names(backup_party)
            # otherwise, set giftee
            person.giftee = giftee

def email(person):
    """
    Sends email from host EMAIL to person, informing of giftee drawn.

    Only works with gmail as-written.

    Args:
        person (dict): party participant's info
    """
    # break person dict into name and info
    for name, info in person.items():
        # build email
        to = info['email']
        subject = 'Secret Santa'
        body = (f"Hello {name}!\n\n"
                f"You are the Secret Santa for {info['giftee']}!\n\n")

        # bring everything together
        email_text = (f"From: {EMAIL}\n"
                      f"To: {to}\n"
                      f"Subject: {subject}\n"
                      f"{body}")

        try:
            # send email
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(EMAIL, EMAIL_APP_PASS)
            server.sendmail(EMAIL, to, email_text)
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
    hat.draw_names(party)

    for person in party.people:
        print(f"{person.name} got {person.giftee}")

    # email participants
    for person in party:
        email(person)
