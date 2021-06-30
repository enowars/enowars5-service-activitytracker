#![feature(proc_macro_hygiene, decl_macro)]
#![feature(option_result_contains)]

pub mod schema;
pub mod models;
pub mod views;
pub mod dbpool;

#[macro_use]
extern crate rocket;
#[macro_use]
extern crate diesel;
extern crate dotenv;
use rocket_contrib::templates::Template;

use std::path::{Path, PathBuf};
use rocket::response::NamedFile;


use dotenv::dotenv;
use std::env;
use rocket::response::Redirect;
use rocket_auth::User;


pub fn establish_connection_pool() -> dbpool::Pool {
    dotenv().ok();

    let config = dbpool::DbConfig{
        host: env::var("DB_HOST").expect("DATABASE_URL must be set"),
        port: 5432,
        user: env::var("DB_USER").expect("DATABASE_URL must be set"),
        password: env::var("DB_PASS").expect("DATABASE_URL must be set"),
        database: env::var("DB_NAME").expect("DATABASE_URL must be set")
    };

    dbpool::init_pool(config)
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

/* Static files Handler for private pictures*/
#[get("/data/imgs/profiles/<file..>")]
fn assets_private(user: User, file: PathBuf) -> Option<NamedFile> {
    println!("{}", file.to_str()?);
    if !file.to_str()?.starts_with(format!("{}.", user.email()).as_str()) {
        return NamedFile::open(Path::new("imgs/default.jpg")).ok();
    }
    if file.to_str()?.contains('\\') {
        return NamedFile::open(Path::new("imgs/default.jpg")).ok();
    }
    if file.to_str()?.contains('/') {
        return NamedFile::open(Path::new("imgs/default.jpg")).ok();
    }
    let path = Path::new((env::var("DATA_DIR").unwrap_or("imgs/".to_string()) + "profiles/").as_str()).join(file);
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

    let pool = establish_connection_pool();

    rocket::ignite().mount("/", routes![
        index,
        assets,
        assets_private,
        views::posts::get_posts_redirect,
        views::posts::get_posts,
        views::posts::my_posts,
        views::posts::friends_posts,
        views::posts::new,
        views::posts::insert,
        views::posts::update,
        views::posts::process_update,
        views::posts::delete,
        views::posts::delete_old,
        views::auth::get_login,
        views::auth::post_login,
        views::auth::get_signup,
        views::auth::post_signup,
        views::auth::logout,
        views::auth::delete,
        views::auth::get_forgot,
        views::auth::post_forgot,
        views::auth::get_addimage,
        views::auth::post_addimage,
        views::auth::get_viewimages,
        views::friends::new,
        views::friends::insert
    ])
        .manage(users)
        .manage(pool)
        .attach(Template::fairing())
        .launch();
}