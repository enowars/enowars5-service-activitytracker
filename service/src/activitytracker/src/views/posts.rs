use diesel::prelude::*;
use crate::schema::*;
use crate::models::posts::*;

use rocket_contrib::templates::Template;
use std::collections::HashMap;

use rocket::request::FlashMessage;
use rocket::response::{Flash, Redirect};

use rocket::http::ContentType;
use rocket::Data;
use rocket_multipart_form_data::{
    MultipartFormData, MultipartFormDataField, MultipartFormDataOptions,
};
use rocket_auth::User;
use serde_json::json;


#[get("/posts")]
pub fn get_posts(user: Option<User>, flash: Option<FlashMessage>) -> Template {
    let posts: Vec<Post> = posts::table
        .filter(posts::deleted.eq(false))
        .load::<Post>(&crate::establish_connection())
        .expect("Could not get posts");

    Template::render("posts/post_list", json!({
            "data": posts,
            "flash": match flash {
                Some(ref msg) => msg.msg(),
                None => "List of posts"
            },
            "user": match user {
                Some(u) => u.email().to_string(),
                None => "".to_string()
            }
        }))
}

#[get("/posts/new")]
pub fn new(user: User, flash: Option<FlashMessage>) -> Template {
    let (m_name, m_msg) = match flash {
        Some(ref msg) => (msg.name(), msg.msg()),
        None => ("success", "Create a new post")
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
    ];

    /* Match the form */
    let multipart_form_data = MultipartFormData::parse(content_type, post_data, options);

    match multipart_form_data {
        Ok(form) => {
            /* Insert data into database */
            create_post(&crate::establish_connection(),
                        match form.texts.get("body") {
                            Some(value) => &value[0].text,
                            None => "",
                        });

            Flash::success(
                Redirect::to("/posts"),
                "Success! You created a new post!",
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


#[get("/posts/update/<id>")]
pub fn update(user: User, flash: Option<FlashMessage>, id: i32) -> Template {
    let post_data = posts::table
        .select(posts::all_columns)
        .filter(posts::id.eq(id))
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
                None => "Create a new post"
             },
            "user": user.email().to_string()
        }))
}

#[post("/posts/update", data = "<post_data>")]
pub fn process_update(user: User, content_type: &ContentType, post_data: Data) -> Flash<Redirect> {
    let mut options = MultipartFormDataOptions::new();
    options.allowed_fields = vec![
        MultipartFormDataField::text("id"),
        MultipartFormDataField::text("body"),
    ];

    let multipart_form_data = MultipartFormData::parse(content_type, post_data, options);

    match multipart_form_data {
        Ok(form) => {

            update_post(&crate::establish_connection(),
                        form.texts.get("id").unwrap()[0]
                            .text
                            .parse::<i32>()
                            .unwrap(),
                        match form.texts.get("body") {
                            Some(value) => &value[0].text,
                            None => "",
                        });
            Flash::success(
                Redirect::to("/posts"),
                "Success! Post updated!",
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

#[get("/posts/delete/<id>")]
pub fn delete(user: User, id: i32) -> Flash<Redirect> {
    delete_post(
        &crate::establish_connection(),
        id
    );
    Flash::success(Redirect::to("/posts"), "The post was deleted.")
}