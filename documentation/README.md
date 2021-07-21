Service documentation - Activitytracker
======================
The activitytracker is a small social network for your fitness needs.

## How does the service work?

There are several features the activitytracker offers, which are described in detail here:

### Authentication

The activitytracker offers authentication for users using the rocket_auth library. Users can create accounts which are stored in the postgres database. When registering, users can optionally upload a 'recovery image'. If they forget their password, they can later change the password by providing the recovery image.

### Posts

#### Creation
Users can create posts that can then be viewed by other users. A post consists of some text (the post `body`), and optionally an `image` uploaded by the user. Users can configure several properties for their posts: they can make a post `protected`, which will prevent editing and deletion of the post, and they can configure post `visibility` to make it visible or hidden for other users.

#### Visibility
There are three visibility settings:
- `public` posts are visible to anyone, even non-registered users
- `friends` posts are visible to your friends only
- `private` posts are only visible to you

#### Editing
Non-protected posts can be edited by their creator. During editing, all properties set during post creation can be changed.

#### Deletion
Non-protected posts can be deleted, which sets their `deleted` field to `true` in the database. Deleted posts don't show up in any of the post lists. 

#### Post lists
Their are several pages where posts can be viewed:
- `/posts/view/<page>` shows all posts visible to the current user, grouped by user who posted them. The e-mail of the user who created a post is shown first, followed by al their visible posts. Per page, 10 users are listed.
- `/posts/my` shows all posts created by the logged in user
- `/posts/friends` shows all posts created by friends of the logged in user

### Friends
Users can add other users as friends, making all posts with visibility `friends` visible to that friend. Friendship is one-sided, and a user can't see the post of the person they added if their weren't added back. To add a friend, their e-mail address is needed. Once added, a friend cannot be deleted.

### Progress pictures
Users can post progress pictures using the `/auth/addimage` endpoint. These images can then be viewed by the user at `/auth/viewimages`. While these images are meant to be a way for users to track their fitness journey, they  are also valid pictures to be used for password recovery.

## Vulnerabilities, Exploits, and Fixes

There are the following vulnerabilities in activitytracker:

### Edit arbitrary posts

- Category: Authorization
- Difficulty: Easy

#### Overview

It is possible to read the contents of any (private, public, or fiends only) post using the edit functionality.

To edit a post, you need its creator's email, and the post ID.

```text
1. register a new user, .e.g email: hanspeter@web.de, password: hanspeter@web.de
2. create a new post
3. click 'edit' on the post
```

You'll get redirected to a URL like `http://localhost:8000/posts/update/hanspeter@web.de/1`
The scheme is `/posts/update/<email>/<id>`. Both the email and the post ID have to match the creator of the post to
be able to edit it. It is not checked whether the logged in user is actually the creator of the post.

```rust
// views/posts.rs 159
#[get("/posts/update/<email>/<id>")]
pub async fn update(user: User, conn: crate::PgDieselDbConn, flash: Option<FlashMessage<'_>>, email: String, id: i32) -> Template {
    /* checks whether the user has rights to edit the post */
    let email_id: i32 = conn.run(move |c| users::table
        .select(users::id)
        .filter(users::email.eq(email))
        .first(c)).await.expect("No such user!");
//  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//  This does not actually check the user's rights to edit a post, it just get's the entered email's user ID
```

#### Attack

```text
1. look at the homepage of the app: http://localhost:8000/posts/view/1
2. there will be some public posts, with the email and friend status of the posts' creators
3. pick one email, e.g. hanspeter@web.de, and try the urls http://localhost:8000/posts/update/hanspeter@web.de/<1 to # of posts>
4. you'll see the edit page and can see the post body in the text box
```


#### Fixes

Fix the access control of the edit page by verifying that the logged in user is the post creator:

```rust
// At the top of update in ln. 160 of views/posts.rs
if email != user.email() {
    panic!("Not permitted to view page!")
}
```


### Insecure password recovery

- Category: Path traversal/Authentication
- Difficulty: Medium

#### Overview

It is possible to reset another user's password to log in as them. For this, we have to smuggle in a recovery image that will be checked in addition to the real image. This can be done by registering a user with a username that is prefixed by the username we want to attack.

```rust
// views/auth.rs 219
let mut matching_image_found = false;
let paths = fs::read_dir(format!("{}profiles", env::var("DATA_DIR").unwrap_or("/".to_string()))).unwrap();
for path in paths {
    let p = path.unwrap().path().display().to_string();
    if p.starts_with(&user_image) {
    // ^^^^^^^^^^^^^^^^^^^^^^^^^^ This only checks the image's prefix, which is not sufficient. 
        if diff(upload_image.to_str().unwrap(), p.as_str()) {
            matching_image_found = true;
            break;
        }
    }
}
```

#### Attack

```text
1. Find a user you want to attack (e.g.: test@test.de)
2. Register a new user that has that username as a prefix and set a password recovery image (e.g.: test@test.de.de)
3. Log out and go to the password recovery form
4. Recover the password of test@test.de
```

#### Fixes

When looking for recovery images to compare the uploaded images against, the filename should be confirmed to exactly follow the naming conventions (e.g. `test@test.de.HH-mm-ss.png` with `HH-mm-ss` being the timestamp when the image was uploaded). A simple fix would be to check whether the user's email address is followed by a period and then exactly 12 characters (`HH-mm-ss.png`), which would not be the case for images uploaded by a users with a suffix after the email address. 

```rust
// Line 223 in views/auth.rs     vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
if p.starts_with(&user_image) && p.len() == user_image.len() + 12 {
```

## Suspicious code that is not a vulnerability

There are several false leads that may appear like a vulnerability, but aren't. In this sections, it is explained what these false leads are and why they're not exploitable.

### Database credentials

The database credentials for the postgres database are hardcoded in the `docker-compose.yml`, they are `diesel:diesel`. It might seem like this is a vulnerability, however, the postgres docker image has no public facing ports and can thus only be accessed from inside the docker network.

### Rocket secret key

Rocket's secret key is hardcoded in the `Rocket.toml`. This secret is used to create private cookies. This can, however, not be used to log in as someone else or to highjack someone else's session:
In `rocket_auth`'s `user/auth.rs`, a session is defined as:

```rust
let session = Session {
    id: user.id,
    email: user.email,
    auth_key: key,
    time_stamp: now() as i32,
};
```

`auth_key` is a randomly generated string of length 15, which cannot be guessed in feasible time. In `rocket_auth`'s `/user/mod.rs`, user authentication is checked as follows:

```rust
fn is_auth(&self, session: &Session) -> bool {
    let option = self.sess.get(session.id);
    if let Some(auth_key) = option {
        auth_key == session.auth_key
    } else {
        false
    }
}
```

To get this function to return `true`, an attacker would not only have to guess a valid session id, but also the associated random auth key, which is not feasible. Thus, it is not possible to highjack another user's session.

As the session object is stored on the server, changing the `id` or `email` field in the cookie won't be helpful in attacking the application either: to get the currently logged in user object, this function is used (from `rocket_auth`'s `users/auth.rs`):

```rust
pub async fn get_user(&self) -> Option<User> {
    if !self.is_auth() {
        return None;
    }
    let id = self.session.as_ref()?.id;
    if let Ok(user) = self.users.get_by_id(id).await {
        Some(user)
    } else {
        None
    }
}
```

The user's `id` that is then used to fetch the user object is taken from the session, which is managed by the server.

This shows that, despite the known secret key, `rocket_auth` cannot be exploited.

### is_admin in the Users model

User objects have an is_admin field, which implicated some hidden admin functionality like login overrides, and admin page, or something similar. No such functionality exists.

### Error message leaks

Some error messages are forwarded directly to the user, which could reveal sensitive information about the application. For instance, in `views/auth.rs`, line `239`, there is this code:

```rust
Err(e) => return Flash::error(
    Redirect::to("/auth/login"),
    format!(
        "User created but error logging in: {}",
        e.to_string()
    ),
),
```

This returns the error message to the user as a flash message. However, these errors contain no useful information, and cannot be used for any attacks.

## What's left to do?

### Mumbles/Errors when attacked

During the CTF, some problems with the service came up. When the password recovery password was used on a team, their service would mumble, or later even error. To fix this problem, one of these fixes can be applied:
- Change password recovery to only log a user in without changing the password (this would require creating a new session by hand, since `rocket_auth` only allows logging in uses if their password is provided, but the password is unknown to the application since it's hashed). Difficulty: `medium`
- Rebrand `password recovery` to `data recovery` and send a user who successfully passed the password recovery check a json of all their viewable posts instead of logging them in. This is, however, pretty unusual functionality and might be a hint for some teams to explore the feature in more detail. Difficulty: `easy`

### Checker improvements

While the checker covers all endpoints and features of the service, the active service looks a bit sterile. While workouts and images are posted during putnoise, the posts that test service functionality are much more prominent. Adding more post-generating functions to the checker that make the service page look more fun and interesting will make the service more appealing to use and play.

This improvement is slightly limited by the current checker functionality: the noise and havoc functions are called only infrequently. It would be nice if there were a category of functions that just get called all the time (i.e., every 10 seconds), to make traffic even more realistic and interesting.