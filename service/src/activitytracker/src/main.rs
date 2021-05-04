#![feature(proc_macro_hygiene, decl_macro)]

pub mod schema;
pub mod models;
pub mod views;

#[macro_use]
extern crate rocket;
#[macro_use]
extern crate diesel;
extern crate dotenv;
use rocket_contrib::templates::Template;

use diesel::prelude::*;
use diesel::pg::PgConnection;
use dotenv::dotenv;
use std::env;


pub fn establish_connection() -> PgConnection {
    dotenv().ok();

    let database_url = env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set");
    PgConnection::establish(&database_url)
        .expect(&format!("Error connecting to {}", database_url))
}


#[get("/")]
fn index() -> String {
    use schema::posts::dsl::*;

    let connection = establish_connection();

    let results = posts.filter(deleted.eq(false))
        .limit(5)
        .load::<models::posts::Post>(&connection)
        .expect("Error loading posts");

    format!("There are {} posts.", results.len())
}

fn main() {

    rocket::ignite().mount("/", routes![
        views::posts::get_posts,
        views::posts::new,
        views::posts::insert,
        views::posts::update,
        views::posts::process_update,
        views::posts::delete,
    ]).attach(Template::fairing()).launch();
}