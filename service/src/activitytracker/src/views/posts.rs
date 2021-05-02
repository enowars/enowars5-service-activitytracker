use diesel::prelude::*;
use crate::schema::*;
use crate::models::posts::*;

use rocket_contrib::templates::Template;
use std::collections::HashMap;

use rocket::request::FlashMessage;


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