use diesel::prelude::*;
use crate::schema::*;
use crate::models::posts::*;
use crate::dbpool;

use rocket_dyn_templates::Template;
use rocket::fs::TempFile;

use rocket::request::FlashMessage;
use rocket::response::{Flash, Redirect};

use rocket::http::ContentType;
use rocket_auth::User;
use serde_json::json;
use std::env;
use crate::models::users::delete_old_users;
use rocket::form::Form;
use std::borrow::{BorrowMut};


const PAGE_SIZE: usize = 10;


#[get("/posts")]
pub fn get_posts_redirect() -> Redirect {
    Redirect::to("/posts/view/0")
}

// from https://www.reddit.com/r/rust/comments/bk7v15/my_next_favourite_way_to_divide_integers_rounding/
fn div_up(a: usize, b: usize) -> usize {
    // We *know* that the hint is exact, this is thus precisely the amount of chunks of length `b` each
    (0..a).step_by(b).size_hint().0
}


#[get("/posts/view/<page>")]
pub fn get_posts(user: Option<User>, conn: dbpool::DbConn, flash: Option<FlashMessage>, page: usize) -> Template {
    let user_id = match user {
        Some(ref u) => u.id(),
        None => -1,
    };
    let uap = UsersAndPosts::load_all(
        user_id,
        PAGE_SIZE,
        page,
        &*conn
    );
    let mut max_users = UsersAndPosts::post_count(user_id, &*conn) as usize;
    if max_users < 1 {
        max_users = 1;
    }
    Template::render("posts/post_list", json!({
            "data": uap,
            "flash": match flash {
                Some(ref msg) => msg.message(),
                None => "List of activities"
            },
            "user": match user {
                Some(u) => u.email().to_string(),
                None => "".to_string()
            },
            "page": page,
            "max_page": div_up(max_users, PAGE_SIZE) - 1,
            "start_page": if page < 4 {0} else {page - 3},
            "end_page": std::cmp::min(div_up(max_users, PAGE_SIZE) - 1, page + 3)
        }))
}

#[get("/posts/my")]
pub fn my_posts(user: User, conn: dbpool::DbConn, flash: Option<FlashMessage>) -> Template {
    let mut uap = UsersAndPosts::load_mine(user.id(),
                                           &*conn
    );
    uap.retain(|u| u.0.id == user.id());

    Template::render("posts/post_list", json!({
            "data": uap,
            "flash": match flash {
                Some(ref msg) => msg.message(),
                None => "List of activities"
            },
            "user": user.email().to_string(),
            "page": 0,
            "max_page": 0,
            "start_page": 0,
            "end_page": 0
        }))
}

#[get("/posts/friends")]
pub fn friends_posts(user: User, conn: dbpool::DbConn, flash: Option<FlashMessage>) -> Template {
    let uap = UsersAndPosts::load_friends(user.id(),
                                          &*conn
    );

    Template::render("posts/post_list", json!({
            "data": uap,
            "flash": match flash {
                Some(ref msg) => msg.message(),
                None => "List of activities"
            },
            "user": user.email().to_string(),
            "page": 0,
            "max_page": 0,
            "start_page": 0,
            "end_page": 0
        }))
}

#[get("/posts/new")]
pub fn new(user: User, flash: Option<FlashMessage>) -> Template {
    let (m_name, m_msg) = match flash {
        Some(ref msg) => (msg.kind(), msg.message()),
        None => ("success", "Create a new activity")
    };
    Template::render("posts/post_new", json!({
            "flash": if m_name == "success" {m_msg} else {""},
            "user": user.email().to_string(),
            "err": if m_name == "error" {m_msg} else {""}
        }))
}

#[derive(Debug, FromForm)]
pub struct PostForm<'v> {
    body: &'v str,
    visibility: &'v str,
    protected: &'v str,
    image: Option<TempFile<'v>>,
}

#[post("/posts/insert", data = "<post_data>")]
pub async fn insert(user: User, conn: dbpool::DbConn, mut post_data: Form<PostForm<'_>>) -> Flash<Redirect> {
    let body = post_data.body;
    let visibility = post_data.visibility;
    let protected = post_data.protected == "true";
    let image = match post_data.image.as_mut() {
        Some(img) => {
            handle_image(img.borrow_mut()).await
        }
        None => None
    };

    /* Insert data into database */
    create_post(&*conn,
                body,
                visibility,
                image,
                user.id(),
                protected
    );

    Flash::success(
        Redirect::to("/posts"),
        "Success! You created a new activity!",
    )
}


#[get("/posts/update/<email>/<id>")]
pub fn update(user: User, conn: dbpool::DbConn, flash: Option<FlashMessage>, email: String, id: i32) -> Template {
    /* checks whether the user has rights to edit the post */
    let email_id: i32 = users::table
        .select(users::id)
        .filter(users::email.eq(email))
        .first(&*conn).expect("No such user!");
    let post_data = posts::table
        .select(posts::all_columns)
        .filter(posts::user_post_count.eq(id))
        .filter(posts::user_id.eq(email_id))
        .load::<Post>(&*conn);

    let (post, err) = match post_data {
        Ok(post) => (post, "".to_string()),
        Err(e) => (vec![], e.to_string())
    };

    Template::render("posts/post_update", json!({
            "post": post,
            "err": err,
            "flash": match flash {
                Some(ref msg) => msg.message(),
                None => "Create a new activity"
             },
            "user": user.email().to_string()
        }))
}


async fn handle_image(image: &mut TempFile<'_>) -> Option<String> {
    let file_name = image.raw_name().unwrap().dangerous_unsafe_unsanitized_raw().as_str();
    let path = format!("imgs/{}", file_name);

    let forbidden_chars = &"#%&{}\\<>*?/ $!'\":@+`|="[..]; // forbidden characters for filenames
    if file_name.contains("..") {   // prevent path traversal
        return None;
    } else if  file_name.contains(forbidden_chars) {
        return None;
    }

    let absolute_path: String = format!("{}{}", env::var("DATA_DIR").unwrap_or("imgs/".to_string()).as_str(), file_name);
    image.copy_to(absolute_path).await.unwrap();

    Some(path)

}


#[derive(Debug, FromForm)]
pub struct PostEditForm<'v> {
    id: i32,
    body: Option<&'v str>,
    visibility: Option<&'v str>,
    image: Option<TempFile<'v>>,
}


#[post("/posts/update", data = "<post_data>")]
#[allow(unused_variables)] // variable user is needed for permissions handler
pub async fn process_update(user: User, conn: dbpool::DbConn, content_type: &ContentType, mut post_data: Form<PostEditForm<'_>>) -> Flash<Redirect> {

    let id = post_data.id;
    let p = posts::table.filter(posts::id.eq(id)).first::<Post>(&*conn).expect("Error updating post.");
    if p.protected {
        return Flash::error(
            Redirect::to("/posts"),
            "This post is protected and cannot be updated."
        );
    }
    if p.user_id != user.id() {
        return Flash::error(
            Redirect::to("/posts"),
            "You cannot update this post."
        );
    }

    let body = post_data.body;
    let visibility = post_data.visibility;

    let image = match post_data.image.as_mut() {
        Some(img) => handle_image(img.borrow_mut()).await,
        None => None
    };


    update_post(&*conn,
                id,
                body,
                visibility,
                image
    );
    Flash::success(
        Redirect::to("/posts"),
        "Success! Activity updated!",
    )
}

#[get("/posts/delete/<email>/<id>")]
#[allow(unused_variables)] // variable user is needed for permissions handler
pub fn delete(user: User, conn: dbpool::DbConn, email: String, id: i32) -> Flash<Redirect> {
    let email_id: i32 = users::table
        .select(users::id)
        .filter(users::email.eq(email))
        .first(&*conn).expect("No such user!");
    let post: Post = posts::table
        .filter(posts::user_id.eq(email_id))
        .filter(posts::user_post_count.eq(id))
        .first(&*conn).expect("No such activity!");
    if post.protected {
        return Flash::error(
            Redirect::to("/posts"),
            "This post is protected and cannot be deleted."
        );
    }
    if post.user_id != user.id() {
        return Flash::error(
            Redirect::to("/posts"),
            "Cannot delete post."
        );
    }
    delete_post(
        &*conn,
        post.id
    );
    Flash::success(Redirect::to("/posts"), "The activity was deleted.")
}

// Clean up every once in a while
#[get("/posts/delete_old")]
pub fn delete_old(conn: dbpool::DbConn) -> Flash<Redirect> {
    delete_old_users(&*conn);
    Flash::success(Redirect::to("/posts"), "Old stuff deleted.")
}