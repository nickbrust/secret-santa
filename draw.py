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
EMAIL = os.environ['EMAIL']
# read email app password from env vars (different from your "normal" password)
EMAIL_APP_PASS = os.environ['EMAIL_APP_PASS']

def draw(hat, person, drawn=None):
    """
    Person draws names from the hat until a valid name is drawn.

    Drawing oneself or a name from one's forbidden list is invalid.

    Args:
        hat (list): list of names still in the hat
        person (dict): person drawing the name
        drawn (list): forbidden names already drawn by person

    Returns:
        str||bool: name drawn or False if valid name is impossible to draw
    """
    # use deepcopy to avoid modifying hat in-place
    hat = deepcopy(hat)
    # break person dict into name and info
    for name, info in person.items():
        # if last name in the hat is the person drawing or in their forbidden
        if len(hat) == 1 and (hat[0] == name or hat[0] in info['forbidden']):
            # return False to signal a full redraw
            return False
        # create empty drawn list on inital call of draw()
        if drawn is None:
            drawn = []
        # draw a random name from the hat
        drawn.append(hat.pop(randint(0, len(hat)-1)))
        # if drawn self or forbidden
        if drawn[-1] == name or drawn[-1] in info['forbidden']:
            print("draw again...")
            # try again, keep track of previously drawn names
            return draw(hat, person, drawn)
        # otherwise return the last (valid) drawn name
        return drawn[-1]

def draw_names(hat, party):
    """
    Cycles through party, having each person draw a name from the hat.

    Performs redraws until a valid conclusion is reached.
    Modifies party in-place by updating each participant's 'giftee'.

    Args:
        hat (list): list of names still in the hat
        party (list): list of participants (dict)
    """
    # use deepcopy to avoid modifying hat and party in-place (used for redraws)
    backup_hat = deepcopy(hat)
    backup_party = deepcopy(party)
    # cycle through party
    for person in party:
        # break person dict into name and info
        for name, info in person.items():
            # draw a name to be giftee
            info['giftee'] = draw(hat, person)
            # False signals a full redraw
            if not info['giftee']:
                print("redraw...")
                return draw_names(backup_hat, backup_party)
            # remove the drawn name from the hat
            hat.remove(info['giftee'])

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


# list of participants from PARTY yaml
party = []
# a simple list of names in PARTY for the "hat"
hat = []
# read PARTY yaml, add giftee key, and build party and hat lists
with open(os.environ['PARTY'], 'r') as yam:
    PARTY = safe_load(yam)
    for person, info in PARTY.items():
        # add key to hold giftee
        info.update({'giftee': ""})
        party.append({person: info})
        hat.append(person)

# run the secret santa drawing
draw_names(hat, party)

# email participants
for person in party:
    email(person)
