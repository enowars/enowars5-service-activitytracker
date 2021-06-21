use diesel::prelude::*;
use crate::schema::*;
use crate::models::posts::*;

use rocket_contrib::templates::Template;

use rocket::request::FlashMessage;
use rocket::response::{Flash, Redirect};

use rocket::http::ContentType;
use rocket::Data;
use rocket_multipart_form_data::{MultipartFormData, MultipartFormDataField, MultipartFormDataOptions, FileField};
use rocket_auth::User;
use serde_json::json;
use std::env;


const PAGE_SIZE: usize = 10;


#[get("/posts")]
pub fn get_posts_redirect() -> Redirect {
    Redirect::to("/posts/0")
}

// from https://www.reddit.com/r/rust/comments/bk7v15/my_next_favourite_way_to_divide_integers_rounding/
fn div_up(a: usize, b: usize) -> usize {
    // We *know* that the hint is exact, this is thus precisely the amount of chunks of length `b` each
    (0..a).step_by(b).size_hint().0
}


#[get("/posts/<page>")]
pub fn get_posts(user: Option<User>, flash: Option<FlashMessage>, page: usize) -> Template {
    let user_id = match user {
        Some(ref u) => u.id(),
        None => -1,
    };
    let uap = UsersAndPosts::load_all(
        user_id,
        PAGE_SIZE,
        page,
        &crate::establish_connection()
    );
    let mut max_users = UsersAndPosts::post_count(user_id, &crate::establish_connection()) as usize;
    if max_users < 1 {
        max_users = 1;
    }
    Template::render("posts/post_list", json!({
            "data": uap,
            "flash": match flash {
                Some(ref msg) => msg.msg(),
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
pub fn my_posts(user: User, flash: Option<FlashMessage>) -> Template {
    let mut uap = UsersAndPosts::load_mine(user.id(),
                                           &crate::establish_connection()
    );
    uap.retain(|u| u.0.id == user.id());

    Template::render("posts/post_list", json!({
            "data": uap,
            "flash": match flash {
                Some(ref msg) => msg.msg(),
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
pub fn friends_posts(user: User, flash: Option<FlashMessage>) -> Template {
    let uap = UsersAndPosts::load_friends(user.id(),
                                          &crate::establish_connection()
    );

    Template::render("posts/post_list", json!({
            "data": uap,
            "flash": match flash {
                Some(ref msg) => msg.msg(),
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
        Some(ref msg) => (msg.name(), msg.msg()),
        None => ("success", "Create a new activity")
    };
    Template::render("posts/post_new", json!({
            "flash": if m_name == "success" {m_msg} else {""},
            "user": user.email().to_string(),
            "err": if m_name == "error" {m_msg} else {""}
        }))
}

#[post("/posts/insert", data = "<post_data>")]
pub fn insert(user: User, content_type: &ContentType, post_data: Data) -> Flash<Redirect> {
    /* Define the form */
    let mut options = MultipartFormDataOptions::new();
    options.allowed_fields = vec![
        MultipartFormDataField::text("body"),
        MultipartFormDataField::text("visibility"),
        MultipartFormDataField::text("protected"),
        MultipartFormDataField::file("image"),
    ];

    /* Match the form */
    let multipart_form_data = MultipartFormData::parse(content_type, post_data, options);

    match multipart_form_data {
        Ok(form) => {
            let image = handle_image(form.files.get("image"));
            /* Insert data into database */
            create_post(&crate::establish_connection(),
                        match form.texts.get("body") {
                            Some(value) => &value[0].text,
                            None => "",
                        },
                        match form.texts.get("visibility") {
                            Some(value) => &value[0].text,
                            None => "private",
                        },
                        image,
                        user.id(),
                        match form.texts.get("protected") {
                            Some(value) => value[0].text.as_str() == "true",
                            None => false
                        }
            );

            Flash::success(
                Redirect::to("/posts"),
                "Success! You created a new activity!",
            )
        },
        Err(err_msg) => {
            /* Falls to this patter if theres some fields that isn't allowed or bolsonaro rules this code */
            Flash::error(
                Redirect::to("/posts/new"),
                format!(
                    "Your form is broken: {}", // TODO: This is a potential debug/information exposure vulnerability!
                    err_msg
                ),
            )
        }
    }
}


#[get("/posts/update/<email>/<id>")]
pub fn update(user: User, flash: Option<FlashMessage>, email: String, id: i32) -> Template {
    /* checks whether the user has rights to edit the post */
    let email_id: i32 = users::table
        .select(users::id)
        .filter(users::email.eq(email))
        .first(&crate::establish_connection()).expect("No such user!");
    let post_data = posts::table
        .select(posts::all_columns)
        .filter(posts::user_post_count.eq(id))
        .filter(posts::user_id.eq(email_id))
        .load::<Post>(&crate::establish_connection());

    let (post, err) = match post_data {
        Ok(post) => (post, "".to_string()),
        Err(e) => (vec![], e.to_string())
    };

    Template::render("posts/post_update", json!({
            "post": post,
            "err": err,
            "flash": match flash {
                Some(ref msg) => msg.msg(),
                None => "Create a new activity"
             },
            "user": user.email().to_string()
        }))
}


fn handle_image(image: Option<&Vec<FileField>>) -> Option<String> {
    use std::fs;
    match image {
        Some(img) => {
            let file_field = &img[0];
            let _content_type = &file_field.content_type;
            let _file_name = &file_field.file_name;
            let _path = &file_field.path;

            let forbidden_chars = &"#%&{}\\<>*?/ $!'\":@+`|="[..]; // forbidden characters for filenames
            if _file_name.as_ref().unwrap().as_str().contains("..") {   // prevent path traversal
                return None;
            } else if  _file_name.as_ref().unwrap().as_str().contains(forbidden_chars) {
                return None;
            }


            let _: Vec<&str> = _file_name.as_ref().unwrap().split('.').collect(); /* Reparsing the fileformat */

            let absolute_path: String = format!("{}{}", env::var("DATA_DIR").unwrap_or("imgs/".to_string()).as_str(), _file_name.clone().unwrap());
            fs::copy(_path, &absolute_path).unwrap();

            Some(format!("imgs/{}", _file_name.clone().unwrap()))
        }
        None => None,
    }
}


#[post("/posts/update", data = "<post_data>")]
#[allow(unused_variables)] // variable user is needed for permissions handler
pub fn process_update(user: User, content_type: &ContentType, post_data: Data) -> Flash<Redirect> {

    let mut options = MultipartFormDataOptions::new();
    options.allowed_fields = vec![
        MultipartFormDataField::text("id"),
        MultipartFormDataField::text("body"),
        MultipartFormDataField::text("visibility"),
        MultipartFormDataField::file("image"),
    ];

    let multipart_form_data = MultipartFormData::parse(content_type, post_data, options);

    match multipart_form_data {
        Ok(form) => {
            let id = form.texts.get("id").unwrap()[0]
                .text
                .parse::<i32>()
                .unwrap();
            let p = posts::table.filter(posts::id.eq(id)).first::<Post>(&crate::establish_connection()).expect("Error updating post.");
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
            let image = handle_image(form.files.get("image"));

            update_post(&crate::establish_connection(),
                        form.texts.get("id").unwrap()[0]
                            .text
                            .parse::<i32>()
                            .unwrap(),
                        match form.texts.get("body") {
                            Some(value) => Some(&value[0].text),
                            None => None,
                        },
                        match form.texts.get("visibility") {
                            Some(value) => Some(&value[0].text),
                            None => None,
                        },
                        image
            );
            Flash::success(
                Redirect::to("/posts"),
                "Success! Activity updated!",
            )
        }
        Err(err_msg) => {
            /* Falls to this patter if theres some fields that isn't allowed or bolsonaro rules this code */
            Flash::error(
                Redirect::to("/posts/update"),
                format!(
                    "Your form is broken: {}", // TODO: This is a potential debug/information exposure vulnerability!
                    err_msg
                ),
            )
        }
    }
}

#[get("/posts/delete/<email>/<id>")]
#[allow(unused_variables)] // variable user is needed for permissions handler
pub fn delete(user: User, email: String, id: i32) -> Flash<Redirect> {
    let email_id: i32 = users::table
        .select(users::id)
        .filter(users::email.eq(email))
        .first(&crate::establish_connection()).expect("No such user!");
    let post: Post = posts::table
        .filter(posts::user_id.eq(email_id))
        .filter(posts::user_post_count.eq(id))
        .first(&crate::establish_connection()).expect("No such activity!");
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
        &crate::establish_connection(),
        post.id
    );
    Flash::success(Redirect::to("/posts"), "The activity was deleted.")
}