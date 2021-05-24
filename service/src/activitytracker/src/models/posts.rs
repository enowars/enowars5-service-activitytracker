use diesel::pg::PgConnection;
use crate::schema::posts;
use crate::schema::users;
use crate::diesel::RunQueryDsl;
use crate::models::posts::posts::dsl as dsl;
use crate::diesel::prelude::*;

use serde::{Serialize};
use crate::models::users::User;
use diesel::expression::dsl::count;


#[derive(Queryable, Serialize, Associations, Identifiable)]
#[belongs_to(User, foreign_key = "user_id")]
pub struct Post {
    pub id: i32,
    pub body: String,
    pub deleted: bool,
    pub visibility: String,
    pub image: Option<String>,
    pub user_id: i32,
    pub user_post_count: i32
}

#[derive(Insertable, AsChangeset)]
#[table_name="posts"]
pub struct NewPost<'a> {
    pub body: &'a str,
    pub visibility: &'a str,
    pub image: Option<String>,
    pub user_id: i32,
    pub user_post_count: i32
}

#[derive(Serialize)]
pub struct UsersAndPosts(User, Vec<Post>);
impl From<(User, Vec<Post>)> for UsersAndPosts {
    fn from(elements: (User, Vec<Post>)) -> Self {
        UsersAndPosts(elements.0, elements.1)
    }
}
impl UsersAndPosts {
    pub fn load_all(email_id: i32, conn: &PgConnection) -> Vec<UsersAndPosts>{
        let users: Vec<User> = users::table.load::<User>(conn).expect("Error loading users").into_iter().rev().collect();
        let posts = Post::belonging_to(&users)
            .filter(posts::deleted.eq(false))
            .filter(posts::visibility.eq("public").or(posts::user_id.eq(email_id)))
            .load::<Post>(conn).expect("Error loading posts")
            .grouped_by(&users);
        users.into_iter().zip(posts).map(UsersAndPosts::from).collect::<Vec<_>>()
    }
}

pub fn create_post(conn: &PgConnection, body: &str, visibility: &str, image: Option<String>, user_id: i32) -> Post {
    let user_post_count = (posts::table
        .select(count(posts::id))
        .filter(posts::user_id.eq(user_id))
        .first::<i64>(&crate::establish_connection()).expect("Error saving post.") + 1) as i32; // Trust me, this is safe!

    let new_post = NewPost {
        body, visibility, image, user_id, user_post_count
    };

    diesel::insert_into(posts::table)
        .values(&new_post)
        .get_result(conn)
        .expect("Error saving post.")
}

pub fn update_post(conn: &PgConnection, id: i32, body: Option<&str>, visibility: Option<&str>, image: Option<String>) -> Post {
    match body {
        Some(b) => {diesel::update(dsl::posts.find(id))
            .set(dsl::body.eq(b))
            .get_result::<Post>(conn)
            .expect("Error updating post.");
            ()
        },
        None => ()
    };
    match visibility {
        Some(v) => {
            diesel::update(dsl::posts.find(id))
                .set(dsl::visibility.eq(v))
                .get_result::<Post>(conn)
                .expect("Error updating post.");
            ()
        },
        None => ()
    };
    match image {
        Some(i) => {
            diesel::update(dsl::posts.find(id))
                .set(dsl::image.eq(i))
                .get_result::<Post>(conn)
                .expect("Error updating post.");
            ()
        },
        None => ()
    };
    posts::table.filter(dsl::id.eq(id)).first(conn).expect("Error loading post.")

}

pub fn delete_post(conn: &PgConnection, id: i32) -> usize {
    diesel::update(dsl::posts.find(id))
        .set(dsl::deleted.eq(true))
        .get_result::<Post>(conn)
        .expect("Error deleting post.");
    1
}