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


#[get("/posts")]
pub fn get_posts(flash: Option<FlashMessage>) -> Template {
    let mut context = HashMap::new();
    let posts: Vec<Post> = posts::table
        .select(posts::all_columns)
        .load::<Post>(&crate::establish_connection())
        .expect("Could not get posts");

    if let Some(ref msg) = flash {
        context.insert("data", (posts, msg.msg()));
    } else {
        context.insert("data", (posts, "List of posts"));
    }

    Template::render("post_list", &context)
}

#[get("/posts/new")]
pub fn new(flash: Option<FlashMessage>) -> Template {
    let mut context = HashMap::new();
    if let Some(ref msg) = flash {
        context.insert("flash", msg.msg());
    }

    Template::render("post_new", context)
}

#[post("/posts/insert", data = "<post_data>")]
pub fn insert(content_type: &ContentType, post_data: Data) -> Flash<Redirect> {

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
            let insert = create_post(&crate::establish_connection(),
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
