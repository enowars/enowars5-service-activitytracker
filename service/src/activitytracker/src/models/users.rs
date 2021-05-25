use diesel::pg::PgConnection;
use crate::schema::users;
use crate::diesel::RunQueryDsl;
use crate::models::users::users::dsl as dsl;
use crate::diesel::prelude::*;
use serde::{Serialize};


#[derive(Queryable, Identifiable, Serialize)]
pub struct User {
    pub id: i32,
    pub email: String,
    pub password: String,
    pub is_admin: bool,
    pub verification_image: String,
}

#[derive(Insertable)]
#[table_name="users"]
pub struct NewUser<'a> {
    pub email: &'a str,
    pub password: &'a str,
    pub is_admin: bool,
    pub verification_image: &'a str,
}

pub fn create_user(conn: &PgConnection, email: &str, password: &str, is_admin: bool, verification_image: &str) -> User {
    let new_user = NewUser {
        email, password, is_admin, verification_image
    };

    diesel::insert_into(users::table)
        .values(&new_user)
        .get_result(conn)
        .expect("Error creating user.")
}

pub fn get_user_id(conn: &PgConnection, email: &str) -> i32 {
    users::table
        .select(dsl::id)
        .filter(dsl::email.eq(email))
        .first(conn)
        .expect("No such user.")
}

pub fn get_user_image(conn: &PgConnection, email: &str) -> String {
    users::table
        .select(dsl::verification_image)
        .filter(dsl::email.eq(email))
        .first(conn)
        .expect("No such user.")
}

pub fn update_user(conn: &PgConnection, id: i32, password: &str) -> User {
    diesel::update(dsl::users.find(id))
        .set(dsl::password.eq(password))
        .get_result(conn)
        .expect("Error updating user.")
}

pub fn update_user_image(conn: &PgConnection, email: &str, image: &str) -> User {
    diesel::update(dsl::users.filter(dsl::email.eq(email)))
        .set(dsl::verification_image.eq(image))
        .get_result(conn)
        .expect("Error updating user.")
}

pub fn delete_user(conn: &PgConnection, id: i32) -> usize {
    diesel::delete(dsl::users.find(id))
        .execute(conn)
        .expect("Error deleting user.")
}