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
use rocket_auth::Users;

use std::path::{Path, PathBuf};
use rocket::response::NamedFile;


use diesel::prelude::*;
use diesel::pg::PgConnection;
use dotenv::dotenv;
use std::env;
use rocket::response::Redirect;


pub fn establish_connection() -> PgConnection {
    dotenv().ok();

    let database_url = env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set");
    PgConnection::establish(&database_url)
        .expect(&format!("Error connecting to {}", database_url))
}


#[get("/")]
fn index() -> Redirect {
    // use schema::posts::dsl::*;
    //
    // let connection = establish_connection();
    //
    // let results = posts.filter(deleted.eq(false))
    //     .limit(5)
    //     .load::<models::posts::Post>(&connection)
    //     .expect("Error loading posts");
    //
    // format!("There are {} posts.", results.len())
    Redirect::to("/posts")
}

/* Static files Handler */
#[get("/imgs/<file..>")]
fn assets(file: PathBuf) -> Option<NamedFile> {
    NamedFile::open(Path::new(env::var("DATA_DIR").unwrap_or("imgs/".to_string()).as_str()).join(file)).ok()
}

fn main() {

    let users = rocket_auth::Users::open_postgres("host=postgres user=diesel password='diesel'").unwrap();

    rocket::ignite().mount("/", routes![
        index,
        assets,
        views::posts::get_posts,
        views::posts::new,
        views::posts::insert,
        views::posts::update,
        views::posts::process_update,
        views::posts::delete,
        views::auth::get_login,
        views::auth::post_login,
        views::auth::get_signup,
        views::auth::post_signup,
        views::auth::logout,
        views::auth::delete
    ])
        .manage(users)
        .attach(Template::fairing())
        .launch();
}