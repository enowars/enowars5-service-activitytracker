use diesel::pg::PgConnection;
use crate::schema::posts;
use crate::diesel::RunQueryDsl;
use crate::models::posts::posts::dsl as dsl;
use crate::diesel::prelude::*;



#[derive(Queryable)]
pub struct Post {
    pub id: i32,
    pub body: String,
    pub deleted: bool,
}

#[derive(Insertable)]
#[table_name="posts"]
pub struct NewPost<'a> {
    pub body: &'a str,
}

pub fn create_post(conn: &PgConnection, body: &str) -> Post {
    let new_post = NewPost {
        body,
    };

    diesel::insert_into(posts::table)
        .values(&new_post)
        .get_result(conn)
        .expect("Error saving post.")
}

pub fn update_post(conn: &PgConnection, id: i32, body: &str) -> Post {
    diesel::update(dsl::posts.find(id))
        .set(dsl::body.eq(body))
        .get_result(conn)
        .expect("Error updating post.")
}

pub fn delete_post(conn: &PgConnection, id: i32) -> usize {
    diesel::update(dsl::posts.find(id))
        .set(dsl::deleted.eq(true))
        .get_result::<Post>(conn)
        .expect("Error deleting post.");
    1
}