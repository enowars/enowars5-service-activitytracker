use diesel::pg::PgConnection;
use crate::schema::chats;
use crate::diesel::RunQueryDsl;
use crate::models::chats::chats::dsl as dsl;
use crate::diesel::prelude::*;


#[derive(Queryable)]
pub struct Chat {
    pub id: i32,
    pub user_1: i32,
    pub user_2: i32,
    pub name: String,
}

#[derive(Insertable)]
#[table_name="chats"]
pub struct NewChat<'a> {
    pub user_1: i32,
    pub user_2: i32,
    pub name: &'a str
}

pub fn create_chat(conn: &PgConnection, user_1: i32, user_2: i32, name: &str) -> Chat {
    let new_chat = NewChat {
        user_1, user_2, name
    };

    diesel::insert_into(chats::table)
        .values(&new_chat)
        .get_result(conn)
        .expect("Error creating chat.")
}

pub fn update_chat(conn: &PgConnection, id: i32, name: &str) -> Chat {
    diesel::update(dsl::chats.find(id))
        .set(dsl::name.eq(name))
        .get_result(conn)
        .expect("Error updating chat.")
}

pub fn delete_post(conn: &PgConnection, id: i32) -> usize {
    diesel::delete(dsl::chats.find(id))
        .execute(conn)
        .expect("Error deleting chat.")
}