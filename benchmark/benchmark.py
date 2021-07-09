import os

import requests
import secrets
from PIL import Image
import random
import time

URL = "http://127.0.0.1:4242"

def generate_random_image(filename):
    im = Image.open('images/profile2.jpg')
    # im = Image.new('RGB', (30, 30))
    pixels = im.load()
    for x in range(min(64, im.size[0])):
        for y in range(min(64, im.size[1])):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    im.save(filename, format='png')
    return filename


email, password = "", ""
POSTS_PAGE = '/posts/view/0'


def register_user(session, use_image=False):
    global email, password
    email = secrets.token_urlsafe(12) + "@gmail.com"
    password = secrets.token_urlsafe(20) + "Aa1"
    if use_image:
        filename = "tmp/" + secrets.token_urlsafe(10) + ".png"
        generate_random_image(filename)
        with open(filename, 'rb') as verification_image:
            resp = session.post(f"{URL}/auth/signup",
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
        resp = session.post(f"{URL}/auth/signup",
                            data={
                                "email": email,
                                "password": password
                            },
                            allow_redirects=False
                            )
    assert(resp.status_code == 303)
    assert(resp.headers['Location'] == POSTS_PAGE)


def login(session):
    global email, password
    resp = session.post(f"{URL}/auth/login",
                        data={
                            "email": email,
                            "password": password
                        })

def get_posts(session, page):
    resp = session.get(f"{URL}/posts/view/{page}")


def create_post(session):
    contents = secrets.token_urlsafe(100)
    resp = session.post(f"{URL}/posts/insert",
                        files={
                            "body": contents,
                            "visibility": "public",
                            "protected": "true"
                        })

def create_post_image(session):
    filename = "tmp/" + "test" + ".png"
    generate_random_image(filename)
    with open(filename, 'rb') as verification_image:
        resp = session.post(f"{URL}/posts/insert",
                            data={
                                "body": "image test 1!",
                                "visibility": "public",
                                "protected": "true"},
                            files={
                                "image": (os.path.basename(filename), verification_image, 'multipart/form-data')
                            })
        # print(resp.text)



to_test = (
    (register_user, (False,), (), "register without image"),
    (register_user, (True,), (), "register with image"),
    (login, (), (), "login"),
    (get_posts, (0,), (), "get posts page 0"),
    (get_posts, (1,), (), "get posts page 1"),
    (create_post, (), ((register_user, (False,)),), "create post"),
    (create_post_image, (), ((register_user, (False,)),), "create post with image"),
)

RUNS = 1

if __name__ == '__main__':
    for fn, args, setup, text in to_test:
        times = []
        for run in range(RUNS):
            s = requests.session()
            for f, a in setup:
                f(s, *a)
            start = time.time()
            fn(s, *args)
            times.append(time.time() - start)
        print(f"{text: <32} : {sum(times)/len(times):.3f}s")