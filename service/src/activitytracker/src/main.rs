#![feature(proc_macro_hygiene, decl_macro)]
#![feature(option_result_contains)]

pub mod schema;
pub mod models;
pub mod views;

#[macro_use]
extern crate rocket;
#[macro_use]
extern crate diesel;
extern crate dotenv;
use rocket_contrib::templates::Template;

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
    Redirect::to("/posts")
}

/* Static files Handler */
#[get("/posts/imgs/<file..>")]
fn assets(file: PathBuf) -> Option<NamedFile> {
    if file.to_str()?.contains('\\') {
        return NamedFile::open(Path::new("imgs/default.jpg")).ok();
    }
    if file.to_str()?.contains('/') {
        return NamedFile::open(Path::new("imgs/default.jpg")).ok();
    }
    let path = Path::new(env::var("DATA_DIR").unwrap_or("imgs/".to_string()).as_str()).join(file);
    if path.exists() {
        NamedFile::open(path).ok()
    } else {
        NamedFile::open(Path::new("imgs/default.jpg")).ok()
    }
}

fn main() {
    dotenv().ok();
    let users = rocket_auth::Users::open_postgres(format!("host={} user={} password='{}'",
        env::var("DB_HOST").expect("DATABASE_URL must be set"),
        env::var("DB_USER").expect("DATABASE_URL must be set"),
        env::var("DB_PASS").expect("DATABASE_URL must be set")
    ).as_str()).unwrap();

    rocket::ignite().mount("/", routes![
        index,
        assets,
        views::posts::get_posts_redirect,
        views::posts::get_posts,
        views::posts::my_posts,
        views::posts::friends_posts,
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
        views::auth::delete,
        views::auth::get_forgot,
        views::auth::post_forgot,
        views::friends::new,
        views::friends::insert
    ])
        .manage(users)
        .attach(Template::fairing())
        .launch();
}