#![feature(proc_macro_hygiene, decl_macro)]

pub mod schema;
pub mod models;

#[macro_use]
extern crate rocket;
#[macro_use]
extern crate diesel;
extern crate dotenv;

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
fn index() -> &'static str {
    "Hello, world!"
}

fn main() {
    use schema::posts::dsl::*;

    let connection = establish_connection();
    let results = posts.filter(deleted.eq(false))
        .limit(5)
        .load::<models::Post>(&connection)
        .expect("Error loading posts");

    println!("There are {} posts.", results.len());

    rocket::ignite().mount("/", routes![index]).launch();
}