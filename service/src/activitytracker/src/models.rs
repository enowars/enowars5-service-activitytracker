#[derive(Queryable)]
pub struct Post {
    pub id: i32,
    pub body: String,
    pub deleted: bool,
}

#[derive(Queryable)]
pub struct User {
    pub id: i32,
    pub username: String,
    pub password: String,
    pub admin: bool,
}

#[derive(Queryable)]
pub struct Chat {
    pub id: i32,
    pub user_1: i32,
    pub user_2: i32,
    pub name: String,
}