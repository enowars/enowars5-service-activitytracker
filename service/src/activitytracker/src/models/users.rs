use diesel::pg::PgConnection;
use crate::schema::users;
use crate::diesel::RunQueryDsl;
use crate::models::users::users::dsl as dsl;
use crate::diesel::prelude::*;


#[derive(Queryable)]
pub struct User {
    pub id: i32,
    pub username: String,
    pub password_hash: String,
    pub admin: bool,
}

#[derive(Insertable)]
#[table_name="users"]
pub struct NewUser<'a> {
    pub username: &'a str,
    pub password_hash: &'a str,
    pub admin: bool
}

pub fn create_user(conn: &PgConnection, username: &str, password_hash: &str, admin: bool) -> User {
    let new_user = NewUser {
        username, password_hash, admin
    };

    diesel::insert_into(users::table)
        .values(&new_user)
        .get_result(conn)
        .expect("Error creating user.")
}

pub fn update_user(conn: &PgConnection, id: i32, password_hash: &str) -> User {
    diesel::update(dsl::users.find(id))
        .set(dsl::password_hash.eq(password_hash))
        .get_result(conn)
        .expect("Error updating user.")
}

pub fn delete_user(conn: &PgConnection, id: i32) -> usize {
    diesel::delete(dsl::users.find(id))
        .execute(conn)
        .expect("Error deleting user.")
}