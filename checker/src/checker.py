#!/usr/bin/env python3
import html

from enochecker import BaseChecker, BrokenServiceException, EnoException, run
from enochecker.utils import SimpleSocket, assert_equals, assert_in
import random
import string
import barnum

#### Checker Tenets
# A checker SHOULD not be easily identified by the examination of network traffic => This one is not satisfied, because our usernames and notes are simple too random and easily identifiable.
# A checker SHOULD use unusual, incorrect or pseudomalicious input to detect network filters => This tenet is not satisfied, because we do not send common attack strings (i.e. for SQL injection, RCE, etc.) in our notes or usernames.
####


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

    ##### EDIT YOUR CHECKER PARAMETERS
    flag_variants = 1
    noise_variants = 2
    havoc_variants = 1
    service_name = "activitytracker"
    port = 4242  # The port will automatically be picked up as default by self.connect and self.http.
    ##### END CHECKER PARAMETERS

    def register_user(self, email: str, password: str):
        self.debug(
            f"Sending command to register user: {email} with password: {password}"
        )
        self.http_get("/auth/signup")
        resp = self.http_post("/auth/signup",
                              data={
                                  "email": email,
                                  "password": password
                              })
        if resp.status_code != 303:
            self.debug(resp)
            raise EnoException(f"Unexpected status code while registering user: {resp.status_code}")

    def login_user(self, email: str, password: str):
        self.debug(
            f"Sending command to login user: {email} with password: {password}"
        )
        self.http_get("/auth/login")
        resp = self.http_post("/auth/login",
                              data={
                                  "email": email,
                                  "password": password
                              })
        if resp.status_code != 303:
            self.debug(resp)
            raise EnoException(f"Unexpected status code while registering user: {resp.status_code}")


    def generate_matching_emails(self, person1, person2, company):
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
            # First we need to register a user. So let's create some random strings. (Your real checker should use some funny usernames or so)
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
            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": f"I love working here at {company} as a {jobtitle}. My boss {boss_firstname} {boss_lastname} is great, and I'll get a promotion soon! Come work here as well! Cheers, {firstname} {lastname}",
                "visibility": "public"
            })
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
        if self.variant_id == 0:
            # First we check if the previous putflag succeeded!
            try:
                username: str = self.chain_db["username"]
                password: str = self.chain_db["password"]
            except IndexError as ex:
                self.debug(f"error getting notes from db: {ex}")
                raise BrokenServiceException("Previous putflag failed.")

            self.debug(f"Connecting to the service")
            self.login_user(username, password)

            # Let´s obtain our note.
            resp = self.http_get('/posts')
            self.debug(self.flag)
            self.debug(resp.text)
            assert_in(
                self.flag, html.unescape(resp.text), "Resulting flag was found to be incorrect"
            )
        else:
            raise EnoException("Wrong variant_id provided")


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
            email = barnum.create_email(name=(firstname, lastname))
            text = barnum.create_sentence(20, 40)

            self.register_user(email, password)

            self.http_get('/posts')
            self.http_get('/posts/new')
            self.http_post('/posts/insert', files={
                "body": text,
                "visibility": "public" if self.variant_id == 0 else "private"
            })
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

            self.debug(f"Connecting to the service")
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
            self.debug(text)
            self.debug(html.unescape(resp.text))
            assert_in(text, html.unescape(resp.text))
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
        # TODO: We still haven't decided if we want to use this function or not. TBA
        pass


app = ActivitytrackerChecker.service  # This can be used for uswgi.
if __name__ == "__main__":
    run(ActivitytrackerChecker)
